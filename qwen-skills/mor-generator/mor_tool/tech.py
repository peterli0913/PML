"""解析放大生产工艺（Tech）docx，得到 process.json。

每个值都带出处（表名、行号或页眉），便于核对。只做抽取，不做推断；推断留给 plan 和人工确认。
"""

import re
import struct
import zipfile

from lxml import etree

from .ooxml import NS, W, clean, q, rows_of, text_of


def _tables(root):
    return root.findall(".//w:body//w:tbl", NS)


def _row_cells(tr):
    out = []
    for tc in tr.findall(q("tc")):
        paras = [clean(text_of(p)) for p in tc.findall(".//w:p", NS)]
        out.append(clean(" ".join(x for x in paras if x)))
    return out


def _row_lines(tr):
    return [[clean(text_of(p)) for p in tc.findall(".//w:p", NS) if clean(text_of(p))] for tc in tr.findall(q("tc"))]


def _checkbox_marks(tc):
    """工艺里用「□」或 FORMCHECKBOX 表示可选操作。"""
    t = text_of(tc)
    return "□" in t or tc.find(".//w:ffData", NS) is not None


def _num(s):
    s = (s or "").replace(",", "").strip()
    m = re.match(r"^-?\d+(\.\d+)?$", s)
    return float(s) if m else None


def _decimals(s):
    s = (s or "").strip()
    return len(s.split(".")[1]) if re.match(r"^-?\d+\.\d+$", s) else 0


def _header_texts(z):
    out = []
    for n in sorted(z.namelist()):
        if re.match(r"word/(header|footer)\d*\.xml$", n):
            x = z.read(n).decode("utf-8")
            out.append("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", x)))
    return out


def _emf_texts(data):
    texts, off = [], 0
    while off + 8 <= len(data):
        typ, size = struct.unpack_from("<II", data, off)
        if size < 8:
            break
        if typ == 84 and off + 52 <= len(data):
            nch, offstr = struct.unpack_from("<II", data, off + 44)
            rec = data[off:off + size]
            texts.append(rec[offstr:offstr + nch * 2].decode("utf-16le", "ignore"))
        off += size
    return texts


def _route_from_images(z):
    """反应路线通常是 ChemDraw 的 EMF，里面能读到分子式和分子量。"""
    best = None
    for n in z.namelist():
        if not n.startswith("word/media/") or not n.lower().endswith(".emf"):
            continue
        txt = "".join(_emf_texts(z.read(n)))
        pairs = re.findall(r"(C\d+H\d+[A-Z][A-Za-z0-9]*?)\s*(\d{2,4}\.\d{1,2})", txt)
        if pairs and (best is None or len(pairs) > len(best["pairs"])):
            best = {"image": n, "text": txt, "pairs": [{"formula": f, "mw": float(m), "mw_text": m} for f, m in pairs]}
    return best


def find_table(tables, *keys):
    for t in tables:
        head = clean(text_of(rows_of(t)[0])) if rows_of(t) else ""
        if all(k in head for k in keys):
            return t
    return None


def parse(path):
    z = zipfile.ZipFile(path)
    root = etree.fromstring(z.read("word/document.xml"))
    tables = _tables(root)
    body_text = clean(text_of(root))
    result = {"source": str(path), "warnings": []}

    heads = " ".join(_header_texts(z))
    m = re.search(r"文件编号[：:]\s*(Tech-([A-Z]+\d?)(\d+?)(\d{2})\s*v\.?\s*(\d+))", heads)
    if m:
        result["tech_no"] = m.group(1).replace(" ", " ")
        result["tech_id"] = "Tech-" + m.group(2) + m.group(3) + m.group(4)
        result["site_code"] = m.group(2)
        result["product_code"] = m.group(3)
        result["step_no"] = m.group(4)
        result["tech_version"] = int(m.group(5))
    else:
        result["warnings"].append("页眉中没有找到 Tech 文件编号")
    m = re.search(r"标题[：:]\s*放大生产工艺\s*(\S+?)放大生产工艺（第(\S+?)版）", heads)
    if m:
        result["title"] = m.group(1)

    info = find_table(tables, "项目主管")
    if info is not None:
        cells = [c for r in rows_of(info) for c in _row_cells(r)]
        kv = {}
        for i in range(0, len(cells) - 1, 2):
            kv[cells[i]] = cells[i + 1]
        result["project_info"] = kv
        step = kv.get("第(  /  )步") or next((v for k, v in kv.items() if k.startswith("第")), "")
        result["step_of"] = step
        result["reaction_name"] = kv.get("反应名称", "")

    plan_tbl = find_table(tables, "计划", "放大")
    overall = {}
    if plan_tbl is not None:
        for r in rows_of(plan_tbl):
            cells = _row_cells(r)
            for i, c in enumerate(cells[:-1]):
                key = c.replace(" ", "")
                if key in ("主原料投料（Kg）", "反应体系（L）", "反应釜规格（L）", "理论产量（Kg）", "预期收率", "产量（Kg）", "产品质量标准要求", "计划放大生产批次"):
                    overall[key] = cells[i + 1]
        result["overall_plan"] = overall
        result["expected_yield"] = overall.get("预期收率", "").replace("%", "")
        result["spec_no"] = overall.get("产品质量标准要求", "")
    else:
        result["warnings"].append("没有找到整体投料计划表")

    feed = find_table(tables, "步骤号", "原料及试剂名称")
    materials = []
    if feed is not None:
        rows = rows_of(feed)
        header = _row_cells(rows[0])
        for idx, r in enumerate(rows[1:], start=2):
            cells = _row_cells(r)
            if len(cells) < 6 or not cells[1]:
                continue
            step_raw = cells[0]
            tc0 = r.findall(q("tc"))[0]
            item = {
                "row": idx,
                "step_raw": step_raw,
                "step": re.sub(r"[^\d]", "", step_raw),
                "limiting": "*" in step_raw,
                "optional": "□" in step_raw or _checkbox_marks(tc0),
                "name": cells[1],
                "fw": cells[2] if len(cells) > 2 else "",
                "qty_kg": cells[3] if len(cells) > 3 else "",
                "volume_m3": cells[4] if len(cells) > 4 else "",
                "density": cells[5] if len(cells) > 5 else "",
                "mol": cells[6] if len(cells) > 6 else "",
                "mol_ratio": cells[7] if len(cells) > 7 else "",
                "l_per_kg": cells[8] if len(cells) > 8 else "",
                "kg_per_kg": cells[9] if len(cells) > 9 else "",
                "nature": cells[10] if len(cells) > 10 else "",
                "qty_decimals": _decimals(cells[3] if len(cells) > 3 else ""),
                "source": "计划投料表 第%d行" % idx,
            }
            materials.append(item)
        result["feed_header"] = header
    else:
        result["warnings"].append("没有找到计划投料表")
    result["materials"] = materials
    lim = [m for m in materials if m["limiting"]]
    result["limiting"] = lim[0] if lim else None
    if not lim:
        result["warnings"].append("投料表里没有带 * 的基准物料")

    ops_tbl = find_table(tables, "步骤", "单元操作名称", "操作步骤")
    ops = []
    if ops_tbl is not None:
        section = ""
        for idx, r in enumerate(rows_of(ops_tbl)[1:], start=2):
            tcs = r.findall(q("tc"))
            cells = _row_cells(r)
            if len(cells) == 1 or (len(cells) >= 1 and cells[0].endswith("操作步骤：")):
                section = cells[0].rstrip("：:")
                continue
            if len(cells) < 3 or not re.search(r"\d", cells[0]):
                continue
            raw = cells[0]
            lines = _row_lines(r)
            text_lines = lines[2] if len(lines) > 2 else []
            ops.append({
                "row": idx,
                "step_raw": raw,
                "step": re.sub(r"[^\d]", "", raw),
                "optional": "□" in raw or _checkbox_marks(tcs[0]),
                "name": cells[1],
                "text": "".join(text_lines) if text_lines else cells[2],
                "text_lines": text_lines,
                "text_has_checkbox": cells[2].lstrip().startswith("□"),
                "duration": cells[3] if len(cells) > 3 else "",
                "hazard": cells[4] if len(cells) > 4 else "",
                "hazard_lines": lines[4] if len(lines) > 4 else [],
                "ppe": cells[5] if len(cells) > 5 else "",
                "section": section,
                "source": "反应及处理操作步骤表 第%d行" % idx,
            })
    else:
        result["warnings"].append("没有找到反应及处理操作步骤表")
    result["operations"] = ops

    samp = find_table(tables, "步骤号", "取样方式")
    sampling = []
    if samp is not None:
        for idx, r in enumerate(rows_of(samp)[1:], start=2):
            cells = _row_cells(r)
            if len(cells) < 4:
                continue
            steps = re.findall(r"(□?)\s*(\d+)", cells[0])
            sampling.append({
                "row": idx,
                "steps_raw": cells[0],
                "steps": [s for _, s in steps],
                "optional_steps": [s for box, s in steps if box],
                "method": cells[1],
                "handling": cells[2],
                "tests": cells[3],
                "ppe": cells[4] if len(cells) > 4 else "",
                "source": "标准取样步骤表 第%d行" % idx,
            })
    result["sampling"] = sampling

    change = find_table(tables, "操作步骤", "更改前", "更改后")
    changes = []
    if change is not None:
        for r in rows_of(change)[1:]:
            cells = _row_cells(r)
            if len(cells) >= 4 and cells[0] not in ("N/A", ""):
                changes.append({"steps": cells[0], "before": cells[1], "after": cells[2], "reason": cells[3], "type": cells[4] if len(cells) > 4 else ""})
    result["changes"] = changes

    pause = re.search(r"建议暂停点[：:]\s*(操作[\d、，,\s]+)", body_text)
    result["pause_points"] = pause.group(1).strip("，, ") if pause else ""

    am = sorted(set(re.findall(r"AM-[\dA-Z]+(?:-\d+)*", body_text)))
    result["analytical_methods_in_tech"] = am

    route = _route_from_images(z)
    if route:
        result["route"] = route
        sm_fw = _num(result["limiting"]["fw"]) if result.get("limiting") else None
        mws = [p for p in route["pairs"]]
        product = None
        if sm_fw is not None:
            others = [p for p in mws if abs(p["mw"] - sm_fw) > 0.005]
            product = others[-1] if others else None
            result["sm_mw_in_route"] = any(abs(p["mw"] - sm_fw) <= 0.005 for p in mws)
        elif mws:
            product = mws[-1]
        if product:
            result["product_mw"] = product["mw_text"]
            result["product_formula"] = product["formula"]
            result["product_mw_source"] = "反应路线图 " + route["image"]
    if "product_mw" not in result:
        result["warnings"].append("没有从反应路线图读到产品分子量，请人工或 AI 看图补充")

    result["is_validation_hint"] = "验证" in body_text[:3000]
    return result
