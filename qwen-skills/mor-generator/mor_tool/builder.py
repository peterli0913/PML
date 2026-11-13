"""按 mor_plan.json 拼装 MOR docx。

以模板为底：前置各节就地填写，正文整段替换成计划里每个 Ins 的块（例子块或库模块），附录保留。
取不到的值一律黄色高亮并写「【待补：…】」，不编造。
"""

import copy
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

from . import mor_doc
from .ooxml import (NS, W, append_text, clean, deep, drop_blue_runs, empty_paragraph, has_sectpr, is_blue, is_pink,
                    make_run, paragraph, pink_to_todo, q, remap_styles, replace_in_runs, rows_of, run_text, set_color,
                    set_highlight, set_paragraph_text, set_repeat_header, set_run_text, set_update_fields, strip_red,
                    text_of)

CJK = re.compile(r"[\u4e00-\u9fff]")


def todo(what, cfg):
    return cfg.common.get("todo_marker", "【待补：{what}】").format(what=what)


class Report:
    def __init__(self):
        self.items = []

    def add(self, where, what, level="todo"):
        self.items.append({"where": where, "what": what, "level": level})


# ---------------------------------------------------------------- 通用小工具

def _paras(el):
    return list(el.iter(q("p")))


def _find_para(els, starts, exact=False):
    for el in els:
        if el.tag != q("p"):
            continue
        t = clean(text_of(el))
        if (t == starts) if exact else t.startswith(starts):
            return el
    return None


def _body_index(body, el):
    return list(body).index(el)


def fill_pink_groups(p, resolver, highlight_missing=True):
    """段落里连续的粉色 run 视为一个槽位。resolver(前面的标签文字, 槽位原文) 返回填入值；None 表示不动。"""
    runs = [r for r in p.iter(q("r"))]
    label = ""
    i = 0
    while i < len(runs):
        r = runs[i]
        if not is_pink(r) or not run_text(r):
            label += run_text(r)
            i += 1
            continue
        label = label[-40:]
        j = i
        group = []
        while j < len(runs) and (is_pink(runs[j]) or not run_text(runs[j])):
            if run_text(runs[j]):
                group.append(runs[j])
            j += 1
        original = "".join(run_text(x) for x in group)
        value = resolver(label, original)
        if value is not None:
            set_run_text(group[0], value[0] if isinstance(value, tuple) else value)
            set_color(group[0], None)
            if isinstance(value, tuple) and value[1]:
                set_highlight(group[0])
            for x in group[1:]:
                set_run_text(x, "")
                set_color(x, None)
        label = ""
        i = j


def set_cell_text(tc, text, highlight=False):
    ps = tc.findall(q("p"))
    if not ps:
        p = etree.SubElement(tc, q("p"))
        ps = [p]
    set_paragraph_text(ps[0], text, highlight=highlight)
    for p in ps[1:]:
        tc.remove(p)
    for r in ps[0].iter(q("r")):
        set_color(r, None)


def set_cell_lines(tc, lines):
    """lines: [(text, highlight)]，一行一个段落，沿用第一段的格式。"""
    ps = tc.findall(q("p"))
    proto = deep(ps[0]) if ps else etree.Element(q("p"))
    for p in ps:
        tc.remove(p)
    for text, hl in lines or [("", False)]:
        p = deep(proto)
        set_paragraph_text(p, text, highlight=hl)
        for r in p.iter(q("r")):
            set_color(r, None)
            if hl:
                set_highlight(r)
        tc.append(p)


def _row_has(tr, s):
    return s in clean(text_of(tr))


# ---------------------------------------------------------------- 前置各节

def fill_front(body, plan, cfg, rep):
    els = list(body)
    meta, front = plan["meta"], plan["front"]
    mor_no = meta["mor_no"] or todo("MOR编号", cfg)
    site = front["site_address"]

    p = _find_para(els, "MOR Number and Ver")
    if p is not None:
        fill_pink_groups(p, lambda lab, orig: mor_no)
    p = _find_para(els, "Production Site Address")
    if p is not None:
        nxt = p.getnext()
        if nxt is not None and nxt.tag == q("p"):
            set_paragraph_text(nxt, site["value"] or todo("厂区地址（rules/sites.yaml 中补充 %s）" % meta["site_code"], cfg),
                               highlight=not site["value"])
            for r in nxt.iter(q("r")):
                set_color(r, None)
                if not site["value"]:
                    set_highlight(r)
            if not site["value"]:
                rep.add("首页", "厂区地址未配置：rules/sites.yaml 的 %s" % meta["site_code"])
    name = front["product_name_en"]
    for p in els:
        if p.tag == q("p") and "Chemical name of this step" in clean(text_of(p)):
            v = name["value"] or todo("产品化学名称", cfg)
            set_paragraph_text(p, v, highlight=not name["value"])
            for r in p.iter(q("r")):
                set_color(r, None)
                if not name["value"]:
                    set_highlight(r)
            if not name["value"]:
                rep.add("首页", "产品化学名称需自填（批注 5）")
            break
    tbl = mor_doc.find_table_after(etree.ElementTree(body.getparent()).getroot(), "试剂、原料和中间体/产品的代码表", "Material Name")
    if tbl is None:
        for el in els:
            if el.tag == q("tbl") and "Material Name" in clean(text_of(rows_of(el)[0])) and "Control Number" in clean(text_of(rows_of(el)[0])):
                tbl = el
                break
    if tbl is not None and len(rows_of(tbl)) > 1:
        cells = rows_of(tbl)[1].findall(q("tc"))
        vals = [(name["value"] or todo("产品名称", cfg), not name["value"]), (front["product_code"]["value"], False),
                (front["client_code"]["value"], True), ("N/A", False)]
        for tc, (v, hl) in zip(cells, vals):
            set_cell_text(tc, v, highlight=hl)
        rep.add("代码表", "客户代码默认 N/A，有客户代码时修改", "check")
    for p in els:
        if p.tag == q("p") and clean(text_of(p)).startswith("Operation Record for"):
            fill_pink_groups(p, lambda lab, orig: front["product_code"]["value"] + " ")
            break

    _approvals(body, cfg, rep)
    _product_info(body, plan, cfg, rep)


def is_final_step(plan):
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)", plan["meta"].get("step_of") or "")
    return bool(m) and m.group(1) == m.group(2)


CHOICES = {
    "intermediate/product": ("product", "intermediate"),
    "intermediate/finished product": ("finished product", "intermediate"),
    "中间体/产品": ("产品", "中间体"),
}


def resolve_choices(elements, final):
    """模板里「中间体/产品」这类二选一的粉字：终产品步骤保留「产品」，中间体步骤保留「中间体」。"""
    for el in elements:
        for p in el.iter(q("p")):
            if not any(is_pink(r) for r in p.iter(q("r"))):
                continue
            full = clean(text_of(p))
            if "MW of" in full or "分子量" in full:
                pink_to_black_el(p)
                continue

            def res(label, orig):
                key = orig.strip().lower().replace(" ", "")
                for k, (fin, mid) in CHOICES.items():
                    if key == k.replace(" ", ""):
                        val = fin if final else mid
                        if orig.strip()[:1].isupper():
                            val = val[:1].upper() + val[1:]
                        return orig.replace(orig.strip(), val)
                return None
            fill_pink_groups(p, res)


def rebuild_toc(body, plan):
    """目录里模板示例的 Ins 条目换成本 MOR 的操作列表。页码在 Word 打开更新目录时生成。"""
    toc = [p for p in body.iter(q("p")) if re.match(r"^(FORMCHECKBOX\s*)?Ins\.\d+/操作\d+[：:]", clean(text_of(p)))
           and p.find(".//w:pStyle", NS) is not None and p.find(".//w:pStyle", NS).get(q("val")) not in ("1", "2", "3")]
    toc = [p for p in toc if p.getparent() is body]
    if not toc:
        return
    proto = deep(toc[0])
    anchor = toc[0]
    for e in plan["ins"]:
        p = deep(proto)
        runs = [r for r in p.iter(q("r")) if run_text(r)]
        label = ("□" if e["optional"] else "") + "Ins.%d/操作%d：%s/%s" % (e["n"], e["n"], e["title_en"], e["title_cn"])
        if runs:
            set_run_text(runs[0], label)
            for r in runs[1:]:
                if not re.fullmatch(r"\s*\d+\s*", run_text(r)):
                    set_run_text(r, "")
                else:
                    set_run_text(r, "")
        anchor.addprevious(p)
    for p in toc:
        body.remove(p)


def _approvals(body, cfg, rep):
    validation = cfg.validation
    for el in list(body):
        t = clean(text_of(el))
        if el.tag == q("tbl") and ("The head of production management" in t or "The head of quality management" in t):
            if not validation:
                body.remove(el)
            else:
                pink_to_black_el(el)
        elif el.tag == q("p") and "{{customersign}}" in t and not cfg.template.get("client_approval", False):
            body.remove(el)
        elif el.tag == q("p") and ("No need for customer approval" in t or "client signature is not required" in t):
            pink_to_black_el(el)


def pink_to_black_el(el):
    for r in el.iter(q("r")):
        if is_pink(r):
            set_color(r, None)


def _product_info(body, plan, cfg, rep):
    front = plan["front"]
    y, sm, pm = front["expected_yield"], front["sm_mw"], front["product_mw"]
    for el in list(body):
        if el.tag != q("p"):
            continue
        t = clean(text_of(el))
        if t.startswith("Expected yield"):
            fill_pink_groups(el, lambda lab, orig: ("     %s       %%  " % y["value"]) if y["value"] else (todo("预期收率", cfg), True))
        elif t.startswith("Theoretical output") and "weight assay percent" in t and cfg.template.get("theoretical_formula", "simple") == "simple":
            body.remove(el)
        elif t.startswith("Theoretical output") and "MW of starting material" in t:
            blues = [r for r in el.iter(q("r")) if is_blue(r) and run_text(r).strip()]
            nums = [r for r in blues if re.fullmatch(r"\s*\d+\.\d+\s*", run_text(r))]
            for r, item in zip(nums, (sm, pm)):
                set_run_text(r, " %s " % (item["value"] or todo("分子量", cfg)))
                set_color(r, None)
                if not item["value"]:
                    set_highlight(r)
            pink_to_black_el(el)
            if not clean(text_of(el)).endswith("kg"):
                append_text(el, "kg")
            if not pm["value"]:
                rep.add("产品信息", "产品分子量没有读到，请看反应路线图填写")
        elif t.startswith("Corrected output") and "seed quantity" in t:
            body.remove(el)
        elif t.startswith("Physical yield"):
            body.remove(el)
        elif t.startswith("Corrected yield"):
            pink_to_black_el(el)
        elif "specifications (for" in t:
            code = front["product_code"]["value"]

            def res(lab, orig):
                o = orig.strip()
                if o in ("客户代码",):
                    return ""
                if re.fullmatch(r",?\s*\d{4,}", o):
                    return code
                return orig
            fill_pink_groups(el, res)
    for el in body.iter(q("tbl")):
        rows = rows_of(el)
        if rows and "Test Description" in clean(text_of(rows[0])) and "Acceptance Criteria" in clean(text_of(rows[0])):
            if len(rows) > 1:
                tc = rows[1].findall(q("tc"))[0]
                spec = front["spec"]["value"].replace("（现行版）", "（Current version/现行版）")
                set_cell_text(tc, spec or todo("质量标准编号", cfg), highlight=not spec)
                if len(rows[1].findall(q("tc"))) > 2:
                    set_cell_text(rows[1].findall(q("tc"))[2], "")
            break


# ---------------------------------------------------------------- 设备清单

def _equipment_groups(tbl):
    rows = rows_of(tbl)
    groups, cur = [], None
    for tr in rows[1:]:
        cells = tr.findall(q("tc"))
        name_idx = 1 if len(cells) > 1 else 0
        name = clean(text_of(cells[name_idx])) if cells else ""
        if "Equipment #" in name or "设备编号" in name:
            cur = {"name": name, "rows": [tr]}
            groups.append(cur)
        elif cur is not None and not name and any(clean(text_of(c)) for c in cells):
            cur["rows"].append(tr)
        else:
            cur = None
    blanks = [tr for tr in rows[1:] if not any(clean(text_of(c)) for c in tr.findall(q("tc")))]
    return groups, blanks


def fill_equipment(body, plan, cfg, rep):
    els = list(body)
    head = _find_para(els, "Pre-batch Equipment Confirmation Checklist")
    if head is None:
        rep.add("设备清单", "模板里没有找到设备检查确认表")
        return
    tables = []
    el = head.getnext()
    while el is not None and len(tables) < 2:
        if el.tag == q("tbl"):
            tables.append(el)
        if el.tag == q("p") and clean(text_of(el)).startswith("Note"):
            break
        el = el.getnext()
    if not tables:
        return
    keep = tables[0]
    if len(tables) > 1 and cfg.template.get("equipment_table", "first") == "first":
        prev = tables[1].getprevious()
        if prev is not None and prev.tag == q("p") and ("厂房和车间" in clean(text_of(prev)) or "4类API" in clean(text_of(prev))):
            body.remove(prev)
        body.remove(tables[1])
    groups, blanks = _equipment_groups(keep)
    blank_proto = deep(blanks[-1]) if blanks else None
    for g in groups:
        for tr in g["rows"]:
            keep.remove(tr)
    for tr in blanks:
        keep.remove(tr)
    fmt = cfg.common.get("ins_reference_format", "Ins.{n}")
    join = cfg.common.get("ins_reference_join", ", ")
    for item in plan["equipment"]:
        proto = _pick_equipment_proto(groups, item)
        need = max(1, len(item["meters"]))
        rows = [deep(r) for r in proto["rows"]]
        while len(rows) < need:
            rows.append(deep(proto["rows"][-1] if len(proto["rows"]) > 1 else proto["rows"][0]))
        rows = rows[:need]
        refs = join.join(fmt.format(n=n) for n in item["ins"])
        eq_no = "_________"
        if cfg.validation:
            eq_no = item.get("equipment_no") or todo("设备编号（取自流程图）", cfg)
        for k, tr in enumerate(rows):
            cells = tr.findall(q("tc"))
            if k == 0:
                set_cell_text(cells[0], refs)
                set_cell_text(cells[1], "%s/ %s Equipment # 设备编号:%s" % (item["en"], item["cn"], eq_no),
                              highlight=cfg.validation and not item.get("equipment_no"))
                set_cell_text(cells[2], item["function"])
            else:
                for c in cells[:3]:
                    set_cell_text(c, "")
            meter_cell = _meter_cell(cells)
            if meter_cell is not None:
                set_cell_text(meter_cell, item["meters"][k] if k < len(item["meters"]) else ("N/A" if not item["meters"] else ""))
            for c in cells:
                strip_red(c)
            keep.append(tr)
    for _ in range(cfg.common["blank_rows"]["equipment_list"]):
        if blank_proto is not None:
            keep.append(deep(blank_proto))
    rep.add("设备清单", "设备按工艺文字识别，共 %d 类；请核对名称、用途和操作号" % len(plan["equipment"]), "check")


def _meter_cell(cells):
    for c in cells:
        t = clean(text_of(c))
        if "Pressure meter" in t or "Thermometer" in t or "Digital display" in t or "Temperature transmitter" in t or t == "N/A":
            return c
    return cells[-2] if len(cells) >= 2 else None


def _pick_equipment_proto(groups, item):
    want = item["en"].lower().rstrip("0123456789")
    for g in groups:
        if want and want.split()[0] in g["name"].lower() and len(g["rows"]) >= max(1, len(item["meters"])):
            return g
    for g in groups:
        if len(g["rows"]) == max(1, len(item["meters"])):
            return g
    return groups[0]


# ---------------------------------------------------------------- 原料信息

def _columns(tr):
    return [clean(text_of(c)) for c in tr.findall(q("tc"))]


def fill_materials(body, plan, cfg, rep):
    els = list(body)
    lim_p = _find_para(els, "Limiting material")
    non_p = _find_para(els, "Non-Limiting material")
    blank_n = cfg.common["blank_rows"]["material_table"]

    def table_after(p):
        el = p.getnext() if p is not None else None
        while el is not None:
            if el.tag == q("tbl"):
                return el
            el = el.getnext()
        return None

    for p, limiting in ((lim_p, True), (non_p, False)):
        tbl = table_after(p)
        if tbl is None:
            continue
        rows = rows_of(tbl)
        header = _columns(rows[0])
        proto = rows[1] if len(rows) > 1 else None
        tail = rows[2:] if limiting else []
        for tr in rows[1:]:
            tbl.remove(tr)
        mats = [m for m in plan["materials"] if m["limiting"] == limiting]
        for m in mats:
            tr = deep(proto)
            cells = tr.findall(q("tc"))
            vals = _material_values(m, header, cfg)
            for c, (v, hl) in zip(cells, vals):
                set_cell_text(c, v, highlight=hl)
            tbl.append(tr)
            if m["en_status"] != "ok":
                rep.add("原料信息", "「%s」英文名需 AI 或人工补充" % m["cn"])
        if not limiting:
            for _ in range(blank_n):
                tr = deep(proto)
                for c in tr.findall(q("tc")):
                    set_cell_text(c, "")
                tbl.append(tr)
        for tr in tail:
            strip_red(tr)
            tbl.append(tr)
    if not cfg.validation:
        rep.add("原料信息", "非验证项目：标准投料量和可接受称量范围留空", "check")


def _material_values(m, header, cfg):
    out = []
    ins = ("□" if m.get("ins_optional") else "") + str(m["ins"]) + ("*" if m["limiting"] else "")
    for h in header:
        if "Operation Instruction" in h:
            out.append((ins, False))
        elif "material name" in h.lower():
            en = m["en"] or todo("英文名", cfg)
            out.append(("%s /%s" % (en, m["cn"]), not m["en"]))
        elif "Density" in h:
            out.append((m["density"] or "--", False))
        elif "Mol. Wt" in h:
            out.append((m["fw"] or "--", False))
        elif "Qty Ratio" in h:
            out.append((m["kg_per_kg"] or "--", False))
        elif "Mol Ratio" in h:
            out.append((m["mol_ratio"] or "--", False))
        elif "Standard Qty" in h:
            out.append((m.get("standard_qty", "") if cfg.validation else "", False))
        elif "Weighing accuracy" in h:
            out.append((m["accuracy"], False))
        elif "Acceptable weighing range" in h:
            out.append((m.get("range", "") if cfg.validation else "", False))
        else:
            out.append(("", False))
    return out


# ---------------------------------------------------------------- 分析方法

def fill_sampling(body, plan, cfg, rep):
    tbl = None
    for el in body.iter(q("tbl")):
        rows = rows_of(el)
        if rows and "Sample Type" in clean(text_of(rows[0])) and "Instruction No" in clean(text_of(rows[0])):
            tbl = el
            break
    if tbl is None:
        return
    rows = rows_of(tbl)
    proto = rows[2] if len(rows) > 2 else rows[-1]
    width = len(proto.findall(q("tc")))
    blank = None
    for tr in rows[2:]:
        if not any(clean(text_of(c)) for c in tr.findall(q("tc"))) and len(tr.findall(q("tc"))) == width:
            blank = tr
        tbl.remove(tr)
    for s in plan["sampling"]:
        ins = ",".join(("□" if n in s.get("optional_ins", []) else "") + str(n) for n in s["ins"])
        if s.get("rows"):
            last_test_row = None
            for k, r in enumerate(s["rows"]):
                tr = deep(proto)
                cells = tr.findall(q("tc"))
                vals = list(r) + [""] * (width - len(r))
                for c, v in zip(cells, vals[:width]):
                    set_cell_text(c, v)
                tbl.append(tr)
                last_test_row = tr
            for t in s.get("added_tests", []):
                en = (s.get("added_en") or {}).get(t, {})
                tr = deep(proto)
                cells = tr.findall(q("tc"))
                vals = [("", False), ("", False), ("", False), ("", False), ("", False),
                        (en.get("test") or t, not en.get("test")), (en.get("criterion") or todo("合格标准", cfg), not en.get("criterion")),
                        (todo("分析方法编号", cfg), True)]
                for c, (v, hl) in zip(cells, vals):
                    set_cell_text(c, v, highlight=hl)
                last_test_row.addnext(tr)
                last_test_row = tr
                rep.add("分析方法", "操作 %s 新增检测项「%s」，请补合格标准和分析方法编号" % (ins, t))
            continue
        tests = [t for t in re.split(r"[，,、；;]\s*|\s+(?=[A-Z]{2,})", s["tests_cn"]) if t.strip()] or [s["tests_cn"]]
        for k, t in enumerate(tests):
            tr = deep(proto)
            cells = tr.findall(q("tc"))
            timely, fio, rel = ("--", "--", "X") if s["release"] else ("X", "--", "--")
            vals = [(ins if k == 0 else "", False), (timely, False), (fio, False), (rel, False),
                    (s["source_desc"] if k == 0 else "", not s["source_desc"] and k == 0),
                    (t, True), (todo("合格标准", cfg), True), (todo("分析方法编号", cfg), True)]
            for c, (v, hl) in zip(cells, vals):
                set_cell_text(c, v, highlight=hl)
            tbl.append(tr)
        rep.add("分析方法", "操作 %s 的检测项需补英文、合格标准和分析方法编号（%s）" % (ins, s["source"]))
    for _ in range(2):
        if blank is not None:
            tbl.append(deep(blank))


# ---------------------------------------------------------------- 正文

def _load_source_elements(entry, session, cache):
    src = entry["source"]
    if src["type"] == "example":
        d = Path(src["dir"])
        key = ("ex", str(d), src["file"])
        if key not in cache:
            root = etree.fromstring((d / src["file"]).read_bytes())
            styles = etree.fromstring((d / "styles.xml").read_bytes())
            cache[key] = (list(root.find("w:body", NS)), styles)
        els, styles = cache[key]
        return [deep(e) for e in els], styles
    if src["type"] == "library" and src.get("module"):
        mid = src["module"]
        if mid.startswith("tpl-"):
            key = ("tpl",)
            if key not in cache:
                z = zipfile.ZipFile(str(session.cfg.resource("template")))
                root = etree.fromstring(z.read("word/document.xml"))
                styles = etree.fromstring(z.read("word/styles.xml"))
                cache[key] = (root, styles)
            root, styles = cache[key]
            mod = next(m for m in session.modules if m["id"] == mid)
            blk = next(b for b in mor_doc.ins_blocks(root) if b["n"] == mod["template_ins"])
            return mor_doc.block_elements(blk), styles
        key = ("lib",)
        if key not in cache:
            z = zipfile.ZipFile(str(session.cfg.resource("library")))
            cache[key] = (etree.fromstring(z.read("word/document.xml")), etree.fromstring(z.read("word/styles.xml")))
        root, styles = cache[key]
        mod = next(m for m in session.modules if m["id"] == mid)
        body = list(root.find("w:body", NS))
        return [deep(body[j]) for j in mod["elements"]], styles
    return [], None


def _header_text(entry):
    return "Ins.%d/操作%d：%s/%s" % (entry["n"], entry["n"], entry["title_en"], entry["title_cn"])


HEADER_ROW = re.compile(r"^(□|☐)?\s*Ins\.\s*(\d+|X)\s*/\s*操作\s*(\d+|X)")


def _is_header_row(tr):
    t = clean(text_of(tr)).replace("FORMCHECKBOX", "").strip()
    return bool(HEADER_ROW.match(t)) and len(tr.findall(q("tc"))) <= 2


def _renumber_headers(els, entry):
    """操作号行改成新的编号。只有首行是操作号行的表才设「跨页重复标题行」：
    重复一大段内容行会让 Word/LibreOffice 排版死循环。"""
    for el in els:
        if el.tag != q("tbl"):
            continue
        rows = rows_of(el)
        for tr in rows:
            if _is_header_row(tr):
                p = tr.find(".//w:p", NS)
                for extra in tr.findall(".//w:p", NS)[1:]:
                    extra.getparent().remove(extra)
                label = ("□" if entry["optional"] else "") + _header_text(entry)
                set_paragraph_text(p, label)
                for r in p.iter(q("r")):
                    set_color(r, None)
                    rpr = r.find(q("rPr"))
                    if rpr is not None and rpr.find(q("b")) is None:
                        etree.SubElement(rpr, q("b"))
        if rows and _is_header_row(rows[0]):
            set_repeat_header(el, True)
        elif rows:
            set_repeat_header(el, False)
            _prepend_header_row(el, entry)


def _prepend_header_row(tbl, entry):
    """库模块的续表没有操作号行时，补一行，保证每张表都带操作号（批注 175）。"""
    rows = rows_of(tbl)
    proto = rows[0]
    tr = deep(proto)
    cells = tr.findall(q("tc"))
    for c in cells[1:]:
        tr.remove(c)
    tc = cells[0]
    tcpr = tc.find(q("tcPr"))
    grid = tbl.find("w:tblGrid", NS)
    span = len(grid.findall(q("gridCol"))) if grid is not None else 1
    if tcpr is None:
        tcpr = etree.SubElement(tc, q("tcPr"))
        tc.remove(tcpr)
        tc.insert(0, tcpr)
    for x in tcpr.findall(q("gridSpan")) + tcpr.findall(q("vMerge")) + tcpr.findall(q("tcW")):
        tcpr.remove(x)
    if span > 1:
        gs = etree.Element(q("gridSpan"))
        gs.set(q("val"), str(span))
        tcpr.insert(1 if tcpr.find(q("cnfStyle")) is not None else 0, gs)
    for p in tc.findall(q("p"))[1:]:
        tc.remove(p)
    for x in list(tc):
        if x.tag not in (q("tcPr"), q("p")):
            tc.remove(x)
    if tc.find(q("p")) is None:
        etree.SubElement(tc, q("p"))
    label = ("□" if entry["optional"] else "") + _header_text(entry)
    set_paragraph_text(tc.find(q("p")), label)
    for r in tc.iter(q("r")):
        set_color(r, None)
        set_highlight(r, None)
        rpr = r.find(q("rPr"))
        if rpr is not None and rpr.find(q("b")) is None:
            etree.SubElement(rpr, q("b"))
    trpr = tr.find(q("trPr"))
    if trpr is not None:
        for x in trpr.findall(q("trHeight")):
            trpr.remove(x)
    proto.addprevious(tr)
    set_repeat_header(tbl, True)


def _cell(els, loc):
    pi, ri, ci = loc[:3]
    if pi >= len(els) or els[pi].tag != q("tbl"):
        return None
    rows = rows_of(els[pi])
    if ri >= len(rows):
        return None
    cells = rows[ri].findall(q("tc"))
    return cells[ci] if ci < len(cells) else None


def _para(els, loc):
    pi, ri, ci, k = loc[:4]
    if ri is None:
        return els[pi] if pi < len(els) else None
    tc = _cell(els, loc)
    if tc is None:
        return None
    ps = tc.findall(q("p"))
    return ps[k] if k < len(ps) else None


def _safety_lines(entry, cfg):
    lines = []
    for s in entry["safety"]:
        en = s["en"] or todo("英文", cfg)
        lines.append(("%s /%s" % (en, s["cn"]), not s["en"]))
    return lines


def _find_library_roles(els):
    roles = {"safety": None, "instruction": None}
    for pi, el in enumerate(els):
        if el.tag != q("tbl"):
            continue
        for ri, tr in enumerate(rows_of(el)):
            if ri == 0:
                continue
            for ci, tc in enumerate(tr.findall(q("tc"))):
                t = clean(text_of(tc))
                if roles["safety"] is None and (t.startswith("Wear ") or "劳保" in t or t.startswith("Hazard and safety")):
                    roles["safety"] = (pi, ri, ci)
                    continue
                if roles["instruction"] is None:
                    for k, p in enumerate(tc.findall(q("p"))):
                        pt = clean(text_of(p))
                        if any(is_pink(r) for r in p.iter(q("r"))) and CJK.search(pt) and re.search(r"向|加入|控温|将|使用前|于|反应|降温|升温|调", pt) and not pt.startswith("Wear"):
                            roles["instruction"] = (pi, ri, ci, k)
                            break
        if roles["instruction"]:
            break
    return roles


def _material_swaps(entry, kn):
    """例子块来自别的工艺时，按顺序把例子的物料名换成本工艺的物料名。"""
    src = entry["source"]
    old = src.get("example_materials") or []
    new = entry["materials"]
    swaps = []
    for o, n in zip(old, new):
        if o["cn"] == n["cn"]:
            continue
        swaps.append((o["cn"], n["cn"]))
        t = kn.term("material", o["cn"]) if kn else None
        if t and n["en"]:
            swaps.append((t["en"], n["en"]))
    return swaps


def _adjust_lot_rows(els, entry, rep):
    mats = entry["materials"]
    if not mats:
        return
    for el in els:
        if el.tag != q("tbl"):
            continue
        rows = rows_of(el)
        i = 0
        context = ""
        while i < len(rows):
            t = clean(text_of(rows[i]))
            if not t.startswith("Lot number"):
                if t:
                    context = t
                i += 1
                continue
            start = i + 2 if i + 1 < len(rows) and "Before charging" in clean(text_of(rows[i + 1])) else i + 1
            j = start
            while j < len(rows) and not clean(text_of(rows[j])).strip(" -"):
                j += 1
            blanks = rows[start:j]
            mat = _match_material(context, mats)
            if mat and blanks:
                want = int(mat["rows"])
                have = len(blanks)
                if want > have:
                    for _ in range(want - have):
                        blanks[-1].addnext(deep(blanks[-1]))
                elif want < have:
                    for tr in blanks[want:]:
                        el.remove(tr)
            rows = rows_of(el)
            i = start + (int(mat["rows"]) if (mat and blanks) else len(blanks))
        rows = rows_of(el)


def _match_material(context, mats):
    c = context.lower()
    for m in mats:
        if m["cn"] and m["cn"] in context:
            return m
        if m["en"] and m["en"].lower() in c:
            return m
    return mats[0] if len(mats) == 1 else None


def _control_numbers(els, entry, cfg, rep):
    mats = [m for m in entry["materials"]]
    for el in els:
        for p in el.iter(q("p")):
            t = clean(text_of(p))
            if "内部控制号" not in t:
                continue
            m = _match_material(t, mats) if mats else None
            if m is None:
                continue
            code = m["control_no"]
            hl = m["control_status"] != "ok"
            full = "".join(run_text(r) for r in p.findall(q("r")))
            mo = re.search(r"(内部控制号[：:]\s*)([A-Z]{2}[0-9X]{6}|[A-Z]{2}00XXXX|)", full)
            if mo and mo.group(2):
                replace_in_runs(p, mo.group(2), code or todo("内部控制号", cfg), highlight=hl or not code)
            elif mo:
                replace_in_runs(p, mo.group(1), mo.group(1) + (code or todo("内部控制号", cfg)), highlight=hl or not code)
            if hl or not code:
                rep.add("Ins.%d" % entry["n"], "「%s」内部控制号：%s" % (m["cn"], m["control_note"] or "请确认"))


def _fill_library_placeholders(els, entry, cfg):
    mats = entry["materials"]
    if not mats:
        return
    m = mats[0]
    en, cn = m["en"] or m["cn"], m["cn"]
    for el in els:
        for p in el.iter(q("p")):
            full = "".join(run_text(r) for r in p.findall(q("r")))
            for old, new in (("Weighing of A/A称重", "Weighing of %s/%s称重" % (en, cn)), ("Add A/加A", "Add %s/加%s" % (en, cn)),
                             ("Add A /加A", "Add %s /加%s" % (en, cn)), ("Add A (Time", "Add %s (Time" % en), ("加A (Time", "加%s (Time" % cn)):
                if old in full:
                    replace_in_runs(p, old, new)
            for r in p.iter(q("r")):
                if is_pink(r) and run_text(r).strip() in ("A", "A/A"):
                    prev = "".join(run_text(x) for x in p.findall(q("r")))
                    set_run_text(r, cn if CJK.search(prev[:max(0, prev.find(run_text(r)))][-3:] or "") else en)
                    set_color(r, None)


def build_body_block(entry, session, cache, rep):
    cfg, kn = session.cfg, session.kn
    els, src_styles = _load_source_elements(entry, session, cache)
    if not els:
        p = paragraph(todo("Ins.%d %s/%s 没有可用的模块，请从操作库选择" % (entry["n"], entry["title_en"], entry["title_cn"]), cfg), highlight=True)
        rep.add("Ins.%d" % entry["n"], "没有可用的模块")
        return [p]
    if src_styles is not None:
        for el in els:
            remap_styles(el, src_styles, session.dst_styles)
    _renumber_headers(els, entry)
    src = entry["source"]
    if src["type"] == "example":
        roles = src.get("roles") or {}
        for a, b in _material_swaps(entry, kn):
            for el in els:
                replace_in_runs(el, a, b, highlight=True)
        ins = entry["instruction"]
        pc = _para(els, roles["instruction_cn"]) if roles.get("instruction_cn") else None
        pe = _para(els, roles["instruction_en"]) if roles.get("instruction_en") else None
        if roles.get("safety") and entry["position_in_op"] == 0 and not entry.get("safety_keep"):
            tc = _cell(els, roles["safety"])
            lines = _safety_lines(entry, cfg)
            if tc is not None and (pc is None or pc.getparent() is not tc):
                if lines:
                    set_cell_lines(tc, lines)
                else:
                    tr = tc.getparent()
                    tr.getparent().remove(tr)
        if ins["status"] != "keep" and roles.get("instruction_cn"):
            if pc is not None:
                set_paragraph_text(pc, ins["cn"])
            if pe is not None:
                set_paragraph_text(pe, ins["en"] or todo("英文操作描述", cfg), highlight=not ins["en"])
            elif pc is not None and ins["en"]:
                pc.addprevious(paragraph(ins["en"], like_p=pc))
            if not ins["en"]:
                rep.add("Ins.%d" % entry["n"], "操作描述已更新为新工艺中文，英文需 AI 或人工补充")
        elif ins["status"] != "keep":
            rep.add("Ins.%d" % entry["n"], "例子块里没有定位到操作描述段落，请人工核对是否与新工艺一致")
        if not src.get("same_text"):
            rep.add("Ins.%d" % entry["n"], "复用例子 %s Ins.%s（相似度 %.2f），请核对块内其他数值" % (src["pair_id"], src["ins"], src["score"]), "check")
    else:
        roles = _find_library_roles(els)
        ins = entry["instruction"]
        p_ins = _para(els, roles["instruction"]) if roles["instruction"] else None
        tc_safe = _cell(els, roles["safety"]) if roles["safety"] else None
        if p_ins is not None:
            en = ins["en"] or todo("英文操作描述", cfg)
            set_paragraph_text(p_ins, en, highlight=not ins["en"])
            p_ins.addnext(paragraph(ins["cn"] or todo("中文操作描述", cfg), like_p=p_ins, highlight=not ins["cn"]))
        else:
            rep.add("Ins.%d" % entry["n"], "库模块里没有找到操作描述位置，请手工粘贴")
        if tc_safe is not None:
            lines = _safety_lines(entry, cfg)
            if p_ins is not None and p_ins.getparent() is tc_safe:
                pass
            elif lines:
                set_cell_lines(tc_safe, lines)
            else:
                tr = tc_safe.getparent()
                tr.getparent().remove(tr)
        _fill_library_placeholders(els, entry, cfg)
        rep.add("Ins.%d" % entry["n"], "使用操作库模块「%s」，模块内的备选行请按工况删减" % src.get("title"), "check")
    _adjust_lot_rows(els, entry, rep)
    _control_numbers(els, entry, cfg, rep)
    out = []
    for el in els:
        out.append(el)
        if el.tag == q("tbl"):
            out.append(empty_paragraph())
    return out


def replace_body(body, plan, session, rep):
    els = list(body)
    head = None
    for el in els:
        if el.tag == q("p") and clean(text_of(el)) == "Operation Instructions/操作指令":
            head = el
    if head is None:
        rep.add("正文", "模板里没有找到「Operation Instructions/操作指令」标题")
        return
    i = els.index(head)
    j = i + 1
    while j < len(els) and els[j].tag != q("tbl"):
        j += 1
    k = j + 1
    while k < len(els) and not (els[k].tag == q("p") and has_sectpr(els[k])):
        k += 1
    start = k + 1
    appendix = next(idx for idx in range(start, len(els)) if els[idx].tag == q("p") and clean(text_of(els[idx])).startswith("Appendix"))
    end_sect = max(idx for idx in range(start, appendix) if els[idx].tag == q("p") and has_sectpr(els[idx]))
    for el in els[start:end_sect]:
        body.remove(el)
    anchor = els[end_sect]
    cache = {}
    for entry in plan["ins"]:
        for el in build_body_block(entry, session, cache, rep):
            anchor.addprevious(el)


# ---------------------------------------------------------------- 版本说明、页眉页脚

def fill_version(body, plan, cfg, rep):
    meta = plan["meta"]
    tech_id = (meta["tech_no"] or "").split(" ")[0]
    ver = meta["tech_version"] or 1
    cn_ver = "一二三四五六七八九十"[ver - 1] if 1 <= ver <= 10 else str(ver)
    mor_base = (meta["mor_no"] or "").rsplit(".", 1)[0]
    els = list(body)
    for el in els:
        if el.tag != q("p"):
            continue
        t = clean(text_of(el))
        if t.startswith("1. Reference scale-up process procedure"):
            set_paragraph_text(el, "1. Reference scale-up process procedure: Scale-up Process Procedure of %s, version %d.0" % (tech_id, ver))
        elif t.startswith("参照放大工艺"):
            set_paragraph_text(el, "参照放大工艺：%s放大生产工艺（第%s版）" % (tech_id, cn_ver))
        elif t.startswith("3. This is first version") or t.startswith("此版本为") and "第一版" in t:
            if ver > 1:
                body.remove(el)
            else:
                fill_pink_groups(el, lambda lab, orig: mor_base if "MOR" in orig or orig.strip() in ("A", "01") else orig)
        elif "second version" in t or ("此版本为" in t and "第二版" in t):
            if ver == 1:
                body.remove(el)
            else:
                label = {2: "second", 3: "third", 4: "fourth", 5: "fifth"}.get(ver, "%dth" % ver)
                if t.startswith("3."):
                    set_paragraph_text(el, "3. This is %s version of %s, so the contrast with the last:" % (label, mor_base))
                else:
                    set_paragraph_text(el, "此版本为%s第%s版，与上一版的对比说明如下（或与上一次生产的对比说明）：" % (mor_base, cn_ver))
    for tbl in body.iter(q("tbl")):
        rows = rows_of(tbl)
        if rows and clean(text_of(rows[0])).startswith("Brief description"):
            if ver == 1:
                tbl.getparent().remove(tbl)
                break
            tc = rows[0].findall(q("tc"))[0]
            lines = [("Brief description/更改内容简要描述：", False)]
            for k, c in enumerate(plan["front"].get("changes", []), start=1):
                en = c["en"] or todo("英文", cfg)
                lines.append(("%d．%s/%s" % (k, en, c["cn"]), not c["en"]))
            lines.append(("Details in Change file, Change No./以上更改详细内容见变更文件，编号：", False))
            set_cell_lines(tc, lines)
            break


def fill_headers_footers(parts, plan, cfg):
    meta, front = plan["meta"], plan["front"]
    code = front["product_code"]["value"]
    step = str(int(meta["step_no"])) if meta.get("step_no") and str(meta["step_no"]).isdigit() else (meta.get("step_no") or "")

    def resolver(label, orig):
        lab = label.strip()
        last = re.split(r"\s{2,}", lab)[-1] if lab else ""
        if "MOR #" in last or last.endswith("Ver:"):
            return meta["mor_no"] or orig
        if "Preparation of" in last:
            return code
        if "Step" in last:
            return step
        if "Title" in last:
            return code
        if "MOR #" in lab:
            return meta["mor_no"] or orig
        return None

    for name, root in parts.items():
        for p in root.iter(q("p")):
            t = clean(text_of(p))
            if any(is_pink(r) for r in p.iter(q("r"))):
                fill_pink_groups(p, resolver)
            if t.startswith("Batch size"):
                for r in list(p.iter(q("r"))):
                    if is_blue(r):
                        r.getparent().remove(r)
                full = "".join(run_text(r) for r in p.findall(q("r")))
                mo = re.search(r"\):\s*(\s+)kg", full)
                if mo:
                    replace_in_runs(p, mo.group(0), "):       %s       kg" % front["batch_size"]["value"])
            if t == "厂区地址":
                addr = front["site_address"]["value"]
                set_paragraph_text(p, addr or todo("厂区地址", cfg), highlight=not addr)
                for r in p.iter(q("r")):
                    set_color(r, None)
        drop_blue_runs(root)


# ---------------------------------------------------------------- 入口

def build(plan, session, out_path):
    cfg = session.cfg
    rep = Report()
    tpl = cfg.resource("template")
    z = zipfile.ZipFile(str(tpl))
    doc = etree.fromstring(z.read("word/document.xml"))
    session.dst_styles = etree.fromstring(z.read("word/styles.xml"))
    body = doc.find("w:body", NS)

    fill_front(body, plan, cfg, rep)
    fill_equipment(body, plan, cfg, rep)
    fill_materials(body, plan, cfg, rep)
    fill_sampling(body, plan, cfg, rep)
    resolve_choices(list(body), is_final_step(plan))
    rebuild_toc(body, plan)
    replace_body(body, plan, session, rep)
    fill_version(body, plan, cfg, rep)

    if cfg.common["colors"].get("drop_blue_notes", True):
        drop_blue_runs(body)
    leftover = pink_to_todo(body)
    if leftover:
        rep.add("全文", "还有 %d 处粉色槽位没有填，已改为黄色高亮" % leftover)
    if cfg.common["colors"].get("red_to_black", True):
        strip_red(body)

    parts = {}
    for n in z.namelist():
        if re.match(r"word/(header|footer)\d*\.xml$", n):
            parts[n] = etree.fromstring(z.read(n))
    fill_headers_footers(parts, plan, cfg)
    for root in parts.values():
        pink_to_todo(root)

    settings = etree.fromstring(z.read("word/settings.xml"))
    set_update_fields(settings)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkstemp(suffix=".docx")[1])
    with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED) as zo:
        for item in z.infolist():
            if item.filename == "word/document.xml":
                zo.writestr(item, etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True))
            elif item.filename in parts:
                zo.writestr(item, etree.tostring(parts[item.filename], xml_declaration=True, encoding="UTF-8", standalone=True))
            elif item.filename == "word/settings.xml":
                zo.writestr(item, etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True))
            else:
                zo.writestr(item, z.read(item.filename))
    shutil.move(str(tmp), str(out_path))
    os.chmod(str(out_path), 0o644)
    return rep
