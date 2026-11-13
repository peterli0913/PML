"""复核工具：可以在任何版本的 MOR 上单独运行，生成后跑一次，人工改完再跑一次。

--fix 时会修改文档：
  1. Ins 按出现顺序重新连续编号，并同步设备清单、原料表、分析方法表里的操作号
  2. 每个操作表的第一行设为「跨页重复标题行」，换页自动带出操作号（批注 175）
  3. 打开文档时自动更新目录和页码
不修改：正文里「进行操作13~16」这类文字引用，只在报告里列出，避免误改。
"""

import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

from . import learn, mor_doc, tech
from .ooxml import (NS, clean, is_highlighted, q, rows_of, run_text, set_paragraph_text, set_repeat_header,
                    set_update_fields, text_of)

def _norm_num(s):
    return (re.sub(r"\s+", "", s).replace("oC", "℃").replace("°C", "℃").replace("＜", "<").replace("＞", ">")
            .replace("≦", "≤").replace("≧", "≥"))


NUM_PAT = re.compile(r"\d+(?:\.\d+)?\s*~\s*\d+(?:\.\d+)?\s*(?:℃|oC|°C|h|min|rpm|%)|[≤≥<>＜＞]\s*-?\d+(?:\.\d+)?\s*(?:℃|oC|°C|%|ppm|MPa|h)(?![\d.])")


def _load(path):
    z = zipfile.ZipFile(str(path))
    return z, etree.fromstring(z.read("word/document.xml")), etree.fromstring(z.read("word/settings.xml"))


def _save(z, doc, settings, out_path):
    tmp = Path(tempfile.mkstemp(suffix=".docx")[1])
    with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED) as zo:
        for item in z.infolist():
            if item.filename == "word/document.xml":
                zo.writestr(item, etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True))
            elif item.filename == "word/settings.xml":
                zo.writestr(item, etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True))
            else:
                zo.writestr(item, z.read(item.filename))
    z.close()
    shutil.move(str(tmp), str(out_path))
    os.chmod(str(out_path), 0o644)


def _renumber(doc, blocks, res):
    mapping = {}
    for i, b in enumerate(blocks, start=1):
        if b["n"] != i:
            mapping[b["n"]] = i
    if not mapping:
        return {}
    for b in blocks:
        new = mapping.get(b["n"], b["n"])
        if new == b["n"]:
            continue
        for el, a, bb in b["parts"]:
            rows = rows_of(el)[a:bb] if a is not None else []
            for tr in rows:
                if mor_doc.row_ins_header(tr):
                    p = tr.find(".//w:p", NS)
                    t = clean(text_of(p))
                    set_paragraph_text(p, re.sub(r"Ins\.\s*\d+\s*/\s*操作\s*\d+", "Ins.%d/操作%d" % (new, new), t))
    res["fixed"].append("Ins 重新编号：%s" % "，".join("%d→%d" % kv for kv in sorted(mapping.items())))
    return mapping


def _sync_refs(doc, mapping, res):
    if not mapping:
        return
    def sub_list(text):
        return re.sub(r"(?<![\d.])(\d+)(?![\d.])", lambda m: str(mapping.get(int(m.group(1)), int(m.group(1)))), text)

    count = 0
    for tbl in doc.iter(q("tbl")):
        rows = rows_of(tbl)
        if not rows:
            continue
        head = clean(text_of(rows[0]))
        if not ("Operation Instruction" in head or "Instruction No" in head):
            continue
        for tr in rows[1:]:
            cells = tr.findall(q("tc"))
            if not cells:
                continue
            c0 = cells[0]
            t = clean(text_of(c0))
            if not t or not re.search(r"\d", t):
                continue
            new = re.sub(r"Ins\.(\d+)", lambda m: "Ins.%d" % mapping.get(int(m.group(1)), int(m.group(1))), t) if "Ins." in t else sub_list(t)
            if new != t:
                p = c0.find(q("p"))
                set_paragraph_text(p, new)
                count += 1
    if count:
        res["fixed"].append("同步前置表格里的操作号 %d 处" % count)


def _text_refs(doc, res):
    out = []
    for p in doc.iter(q("p")):
        t = clean(text_of(p))
        for m in re.finditer(r"(进行|执行|重复)操作\s*\d+(?:\s*[~～、和或]\s*\d+)*|[Ii]nstruction\s*\d+|Ins\.\s*\d+\s*~\s*\d+", t):
            out.append(m.group(0))
    if out:
        res["warnings"].append("正文里有 %d 处文字引用了操作号（例如「%s」），编号变动后请人工确认" % (len(out), out[0]))


PAGE_REF = re.compile(r"Page\s*(?:\d+|X{2,})\s*of\s*(?:\d+|Y{2,})")


def _checkbox_fields_to_text(doc):
    """FORMCHECKBOX 域换成「□」。只用于排版副本：LibreOffice 遇到加粗段落里的复选框域会陷入排版死循环，Word 不受影响。"""
    n = 0
    for p in doc.iter(q("p")):
        runs = [r for r in p.iter(q("r"))]
        i = 0
        while i < len(runs):
            fc = runs[i].find(q("fldChar"))
            if fc is None or fc.get(q("fldCharType")) != "begin":
                i += 1
                continue
            depth, j, instr = 0, i, ""
            while j < len(runs):
                f = runs[j].find(q("fldChar"))
                it = runs[j].find(q("instrText"))
                if it is not None:
                    instr += it.text or ""
                if f is not None and f.get(q("fldCharType")) == "begin":
                    depth += 1
                elif f is not None and f.get(q("fldCharType")) == "end":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if "FORMCHECKBOX" not in instr or j >= len(runs):
                i = j + 1
                continue
            first = runs[i]
            for r in runs[i + 1:j + 1]:
                r.getparent().remove(r)
            for child in list(first):
                if child.tag != q("rPr"):
                    first.remove(child)
            t = etree.SubElement(first, q("t"))
            t.text = "□"
            n += 1
            i = j + 1
    return n


def _render_copy(docx_path):
    z = zipfile.ZipFile(str(docx_path))
    doc = etree.fromstring(z.read("word/document.xml"))
    _checkbox_fields_to_text(doc)
    tmp = Path(tempfile.mkdtemp(prefix="mor-render-")) / Path(docx_path).name
    with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED) as zo:
        for item in z.infolist():
            data = z.read(item.filename)
            if item.filename == "word/document.xml":
                data = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
            zo.writestr(item, data)
    z.close()
    return tmp


def render_pages(docx_path):
    """用 LibreOffice 转 PDF，找出「说明」所在页和总页数。没装 LibreOffice 时返回 None。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return None
    import signal
    import subprocess
    out = Path(tempfile.mkdtemp())
    profile = Path(tempfile.mkdtemp(prefix="lo-profile-"))
    proc = subprocess.Popen([soffice, "-env:UserInstallation=file://%s" % profile, "--headless", "--convert-to", "pdf",
                             str(_render_copy(docx_path)), "--outdir", str(out)],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    try:
        proc.wait(timeout=240)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        return None
    pdfs = list(out.glob("*.pdf"))
    if not pdfs:
        return None
    d = pymupdf.open(str(pdfs[0]))
    page = None
    for i, p in enumerate(d):
        t = p.get_text()
        if "Instructions/说明" in t.replace(" ", "") or ("Instructions/" in t and "说明" in t and "Key operation" in t):
            page = i + 1
            break
    return {"instructions_page": page, "total": d.page_count, "pdf": str(pdfs[0])}


def _refresh_page_refs(doc, pages, res):
    if not pages or not pages.get("instructions_page"):
        return
    n = 0
    new = "Page %d of %d" % (pages["instructions_page"], pages["total"])
    for p in doc.iter(q("p")):
        full = "".join(run_text(r) for r in p.iter(q("r")))
        if "Instructions" not in full and "说明" not in full:
            continue
        for m in set(PAGE_REF.findall(full)):
            if m != new:
                from .ooxml import replace_in_runs
                n += replace_in_runs(p, m, new)
    if n:
        res["fixed"].append("「说明」页码引用更新为 %s，共 %d 处（按 LibreOffice 排版估算，Word 打开后请复核）" % (new, n))


def check(mor_path, tech_path=None, fix=False, out_path=None, pages=False):
    res = {"file": str(mor_path), "errors": [], "warnings": [], "fixed": [], "highlights": 0, "todo_texts": []}
    z, doc, settings = _load(mor_path)
    blocks = mor_doc.ins_blocks(doc)
    res["ins_count"] = len(blocks)

    seen = [b["n"] for b in blocks]
    if seen != list(range(1, len(seen) + 1)):
        (res["warnings"] if fix else res["errors"]).append("Ins 编号不连续：%s" % seen)
    mapping = _renumber(doc, blocks, res) if fix else {}
    if fix:
        _sync_refs(doc, mapping, res)
        n_hdr = 0
        for b in blocks:
            for el, a, bb in b["parts"]:
                if a is not None and el.tag == q("tbl"):
                    first = rows_of(el)[0]
                    if mor_doc.row_ins_header(first) and first.find("w:trPr/w:tblHeader", NS) is None:
                        set_repeat_header(el, True)
                        n_hdr += 1
        if n_hdr:
            res["fixed"].append("设置跨页重复标题行 %d 张表" % n_hdr)
        if set_update_fields(settings):
            res["fixed"].append("设置为打开时更新目录和页码")
    _text_refs(doc, res)

    for r in doc.iter(q("r")):
        if is_highlighted(r) and run_text(r).strip():
            res["highlights"] += 1
            if len(res["todo_texts"]) < 400:
                res["todo_texts"].append(run_text(r).strip()[:60])
    page_x = sum(1 for p in doc.iter(q("p")) if "Page XXXX of YYYY" in clean(text_of(p)))
    if page_x:
        res["warnings"].append("还有 %d 处「Page XXXX of YYYY」需要在 Word 里更新目录后按「说明」所在页填写" % page_x)

    for tbl in doc.iter(q("tbl")):
        rows = rows_of(tbl)
        if rows and "Equipment" in clean(text_of(rows[0])) and "Operation Instruction" in clean(text_of(rows[0])):
            empty = sum(1 for tr in rows[1:] if tr.findall(q("tc")) and "设备编号" in clean(text_of(tr)) and not clean(text_of(tr.findall(q("tc"))[0])))
            if empty:
                res["warnings"].append("设备清单有 %d 个设备没有填操作指令编号" % empty)

    if tech_path:
        proc = tech.parse(tech_path)
        _check_against_tech(doc, blocks, proc, res)

    if fix:
        _save(z, doc, settings, out_path or mor_path)
    if fix and pages:
        info = render_pages(out_path or mor_path)
        if info is None:
            res["warnings"].append("没有 LibreOffice，页码引用未更新")
        else:
            z2, doc2, settings2 = _load(out_path or mor_path)
            _refresh_page_refs(doc2, info, res)
            _save(z2, doc2, settings2, out_path or mor_path)
            res["pages"] = info
            res["warnings"] = [w for w in res["warnings"] if "Page XXXX" not in w]
    return res


def _check_against_tech(doc, blocks, proc, res):
    al = learn.align(proc["operations"], blocks)
    for i, bs in al:
        op = proc["operations"][i]
        if not bs:
            res["errors"].append("工艺操作 %s（%s）在 MOR 里没有对应的 Ins" % (op["step_raw"], op["name"]))
        elif op["optional"] or op.get("text_has_checkbox"):
            for b in bs:
                if not blocks[b]["optional"]:
                    res["warnings"].append("工艺操作 %s 是可选操作，Ins.%d 没有复选框" % (op["step_raw"], blocks[b]["n"]))
    tech_text = " ".join(o["text"] + " " + " ".join(o.get("hazard_lines") or []) + " " + (o.get("ppe") or "") for o in proc["operations"])
    tech_text += " " + " ".join(s["tests"] + " " + s["method"] + " " + s["handling"] for s in proc.get("sampling", []))
    tech_nums = {_norm_num(m.group(0)) for m in NUM_PAT.finditer(tech_text.replace("＜", "<").replace("＞", ">"))}
    bad = []
    for b in blocks:
        for p in (x for el, a, bb in b["parts"] for tr in (rows_of(el)[a:bb] if a is not None else [el]) for x in tr.iter(q("p"))):
            t = clean(text_of(p))
            if not re.search(r"[\u4e00-\u9fff]", t):
                continue
            if re.search(r"超温报警|Alarm|报警设置", t):
                continue
            for m in NUM_PAT.finditer(t.replace("＜", "<").replace("＞", ">")):
                v = _norm_num(m.group(0))
                if v not in tech_nums:
                    bad.append("Ins.%d：%s" % (b["n"], v))
    if bad:
        res["warnings"].append("MOR 里有 %d 个参数在工艺操作描述中找不到原文（可能是改写或模板自带）：%s" % (len(bad), "；".join(sorted(set(bad))[:15])))
    mor_mats = {m["name_cn"] for m in mor_doc.material_rows(doc)}
    for m in proc["materials"]:
        if m["name"] not in mor_mats:
            res["errors"].append("工艺物料「%s」（步骤 %s）不在 MOR 原料表里" % (m["name"], m["step_raw"]))


def to_markdown(res):
    lines = ["# MOR 复核报告", "", "文件：%s" % Path(res["file"]).name, "",
             "结果：错误 %d ｜ 提示 %d ｜ 黄色高亮待补 %d ｜ Ins %d 个" % (len(res["errors"]), len(res["warnings"]), res["highlights"], res.get("ins_count", 0)), ""]
    if res["fixed"]:
        lines += ["## 已自动修正", ""] + ["- " + x for x in res["fixed"]] + [""]
    lines += ["## 错误（必须修改）", ""] + (["- " + x for x in res["errors"]] or ["- 无"]) + [""]
    lines += ["## 提示（建议人工确认）", ""] + (["- " + x for x in res["warnings"]] or ["- 无"]) + [""]
    if res["todo_texts"]:
        uniq = []
        for t in res["todo_texts"]:
            if t not in uniq:
                uniq.append(t)
        lines += ["## 高亮待补（去重后前 40 项）", ""] + ["- " + t for t in uniq[:40]] + [""]
    return "\n".join(lines)
