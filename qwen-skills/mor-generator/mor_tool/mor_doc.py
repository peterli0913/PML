"""读取一份已有的 MOR（人工定稿或工具生成），切出操作块和前置各表。"""

import re
import zipfile

from lxml import etree

from .ooxml import NS, clean, has_page_break, has_sectpr, q, rows_of, text_of

INS_RE = re.compile(r"^(?:FORMCHECKBOX|□|☐)?\s*Ins\.\s*(\d+)\s*/\s*操作\s*(\d+)\s*[：:]\s*(.+)$")


def row_ins_header(tr):
    raw = clean(text_of(tr))
    t = raw.replace("FORMCHECKBOX", "").strip()
    if len(tr.findall(q("tc"))) > 2:
        return None
    m = INS_RE.match(t)
    if not m:
        return None
    title = m.group(3).strip()
    en, cn = title, ""
    mm = re.match(r"(.+?)\s*/\s*(.+)", title)
    if mm:
        en, cn = mm.group(1).strip(), mm.group(2).strip()
    return {"n": int(m.group(1)), "title": title, "title_en": en, "title_cn": cn,
            "optional": "FORMCHECKBOX" in raw or "□" in raw}


def ins_header(tbl):
    rows = rows_of(tbl)
    return row_ins_header(rows[0]) if rows else None


def load(path):
    z = zipfile.ZipFile(str(path))
    root = etree.fromstring(z.read("word/document.xml"))
    styles = etree.fromstring(z.read("word/styles.xml"))
    comments = []
    if "word/comments.xml" in z.namelist():
        croot = etree.fromstring(z.read("word/comments.xml"))
        doc_xml = z.read("word/document.xml").decode("utf-8")
        for c in croot.findall("w:comment", NS):
            cid = c.get(q("id"))
            m = re.search(r'<w:commentRangeStart w:id="%s"/>(.*?)<w:commentRangeEnd w:id="%s"/>' % (cid, cid), doc_xml, re.S)
            anchor = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(1))) if m else ""
            comments.append({"id": cid, "author": c.get(q("author")), "text": clean(text_of(c)), "anchor": clean(anchor)[:300]})
    return root, styles, comments


def body_elements(root):
    return list(root.find("w:body", NS))


def ins_blocks(root):
    """按操作号把正文切块。操作号行可能出现在表格中间，所以按行切。

    返回 [{n, title..., parts:[(tbl, start_row, end_row) 或 (p, None, None)]}]。
    每一块的 part 用 block_elements() 还原成独立的表格和段落。
    """
    els = body_elements(root)
    blocks = []
    cur = None
    started = False
    for el in els:
        if el.tag == q("tbl"):
            rows = rows_of(el)
            seg_start = 0
            for ri, tr in enumerate(rows):
                h = row_ins_header(tr)
                if not h:
                    continue
                started = True
                if cur is not None and ri > seg_start:
                    cur["parts"].append((el, seg_start, ri))
                if cur is None or cur["n"] != h["n"]:
                    cur = dict(h, parts=[])
                    blocks.append(cur)
                seg_start = ri
            if started and cur is not None and seg_start < len(rows):
                cur["parts"].append((el, seg_start, len(rows)))
            continue
        if not started:
            continue
        t = clean(text_of(el))
        if t.startswith("Appendix") or t.startswith("附录"):
            break
        if t and cur is not None and not has_sectpr(el):
            cur["parts"].append((el, None, None))
    return blocks


def block_elements(block):
    """把一块还原成可以插进新文档的元素（深拷贝）。表格只保留属于这一块的行。"""
    import copy
    out = []
    for el, a, b in block["parts"]:
        if a is None:
            out.append(copy.deepcopy(el))
            continue
        rows = rows_of(el)
        new = copy.deepcopy(el)
        for tr in rows_of(new):
            new.remove(tr)
        for tr in rows[a:b]:
            new.append(copy.deepcopy(tr))
        out.append(new)
    return out


def block_text(block):
    return " ".join(clean(text_of(tr)) for el, a, b in block["parts"] for tr in (rows_of(el)[a:b] if a is not None else [el]))


def _is_heading(p, heading):
    t = clean(text_of(p))
    return t == heading or (t.startswith(heading) and not re.search(r"\d+$", t))


def toc_titles(root):
    out = []
    for p in root.iter(q("p")):
        t = clean(text_of(p)).replace("FORMCHECKBOX", "").strip()
        m = re.match(r"^Ins\.(\d+)/操作\d+[：:](.+?)(\d+)$", t)
        if m:
            out.append((int(m.group(1)), m.group(2).strip()))
    return out


def find_table_after(root, heading_text, header_contains):
    els = body_elements(root)
    seen = False
    for el in els:
        if el.tag == q("p") and _is_heading(el, heading_text):
            seen = True
        if seen and el.tag == q("tbl"):
            head = clean(text_of(rows_of(el)[0])) if rows_of(el) else ""
            if header_contains in head:
                return el
    return None


def material_rows(root):
    """原料信息两张表：返回 [{ins, name_en, name_cn, mw, density, kg_ratio, mol_ratio, limiting}]。"""
    out = []
    for label, limiting in (("Limiting material", True), ("Non-Limiting material", False)):
        tbl = find_table_after(root, label, "Raw Material Name")
        if tbl is None:
            tbl = find_table_after(root, label, "Raw material name")
        if tbl is None:
            continue
        rows = rows_of(tbl)
        head = [clean(text_of(c)) for c in rows[0].findall(q("tc"))]
        for r in rows[1:]:
            cells = [clean(text_of(c)) for c in r.findall(q("tc"))]
            if len(cells) < 3 or not cells[1] or cells[1].startswith("Entered") or "/" not in cells[1]:
                continue
            en, cn = [x.strip() for x in cells[1].split("/", 1)] if "/" in cells[1] else (cells[1], "")
            item = {"ins": cells[0].replace("*", "").strip(), "name_en": en, "name_cn": cn, "limiting": limiting, "cells": cells}
            for i, h in enumerate(head):
                if "Mol. Wt" in h and i < len(cells):
                    item["mw"] = cells[i]
                if "Density" in h and i < len(cells):
                    item["density"] = cells[i]
                if "Qty Ratio" in h and i < len(cells):
                    item["kg_ratio"] = cells[i]
                if "Mol Ratio" in h and i < len(cells):
                    item["mol_ratio"] = cells[i]
            out.append(item)
    return out


def equipment_rows(root):
    tbl = find_table_after(root, "Equipment Information List/设备使用清单", "Equipment")
    out = []
    if tbl is None:
        return out
    for r in rows_of(tbl)[1:]:
        cells = [clean(text_of(c)) for c in r.findall(q("tc"))]
        for c in cells:
            m = re.match(r"(.+?)\s*Equipment\s*#", c)
            if not m:
                continue
            name = m.group(1).strip()
            first_cjk = re.search(r"[\u4e00-\u9fff]", name)
            if first_cjk:
                cut = first_cjk.start()
                en = name[:cut].rstrip(" /L0123456789").strip() if name[:cut].strip(" /") else ""
                head = name[:cut]
                lead = re.search(r"(\s*/?\s*\d*\s*L?)\s*$", head)
                en = head[:lead.start()].strip(" /") if lead else head.strip(" /")
                cn = (head[lead.start():] if lead else "").strip(" /") + name[cut:]
            else:
                en, cn = name, ""
            out.append({"en": en, "cn": cn.strip(), "cells": cells})
            break
    return out


def sampling_rows(root):
    tbl = find_table_after(root, "Analytical Method/分析方法", "Sample Type")
    out = []
    if tbl is None:
        return out
    for r in rows_of(tbl)[2:]:
        cells = [clean(text_of(c)) for c in r.findall(q("tc"))]
        if any(cells):
            out.append(cells)
    return out


def control_numbers(root):
    out = []
    for p in root.iter(q("p")):
        t = clean(text_of(p))
        m = re.search(r"Weighing of\s*(.+?)\s*/\s*(.+?)称重[：:].*?内部控制号[：:]\s*([A-Z]{2}\d{6})", t)
        if m:
            out.append({"en": m.group(1).strip(), "cn": m.group(2).strip(), "control_no": m.group(3)})
    for tbl in root.iter(q("tbl")):
        for tr in rows_of(tbl):
            t = clean(text_of(tr))
            for m in re.finditer(r"Weighing of\s*(.+?)\s*/\s*(.+?)称重[：:].*?内部控制号[：:]\s*([A-Z]{2}\d{6})", t):
                out.append({"en": m.group(1).strip(), "cn": m.group(2).strip(), "control_no": m.group(3)})
    seen, uniq = set(), []
    for x in out:
        k = (x["cn"], x["control_no"])
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


def bilingual_pairs(text):
    """把「English/中文English/中文」这种拼在一起的双语文字拆成 (中文, 英文) 对。"""
    pairs = []
    for m in re.finditer(r"([A-Za-z0-9][^\u4e00-\u9fff/]{3,}?)\s*/\s*([\u4e00-\u9fff0-9（(][^A-Za-z]*?[\u4e00-\u9fff）)。℃%\d])(?=[A-Z][a-z]|$)", text):
        en, cn = m.group(1).strip(" .;,"), m.group(2).strip()
        if len(en) > 2 and len(cn) > 1:
            pairs.append((cn, en))
    return pairs
