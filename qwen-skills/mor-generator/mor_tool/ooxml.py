"""Word OOXML 的读写小工具。只依赖 lxml；python-docx 只用来打开和保存包。"""

import copy
import re

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W_NS, "r": R_NS}
W = "{%s}" % W_NS

PINK = {"FF00FF", "FF33CC"}
BLUE = {"0000FF", "0033CC", "0000CC"}
TODO_HIGHLIGHT = "yellow"


def q(tag):
    return W + tag


def text_of(el):
    return "".join(t.text or "" for t in el.iter(q("t")))


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\u3000", " ")).strip()


def cell_texts(row):
    return [clean(text_of(c)) for c in row.findall(q("tc"))]


def rows_of(tbl):
    return tbl.findall(q("tr"))


def run_color(r):
    c = r.find("w:rPr/w:color", NS)
    return (c.get(q("val")) or "").upper() if c is not None else ""


def run_text(r):
    return "".join(t.text or "" for t in r.findall(q("t")))


def is_pink(r):
    return run_color(r) in PINK


def is_blue(r):
    return run_color(r) in BLUE


def ensure_rpr(r):
    rpr = r.find(q("rPr"))
    if rpr is None:
        rpr = etree.SubElement(r, q("rPr"))
        r.remove(rpr)
        r.insert(0, rpr)
    return rpr


def set_color(r, val):
    rpr = ensure_rpr(r)
    c = rpr.find(q("color"))
    if val is None:
        if c is not None:
            rpr.remove(c)
        return
    if c is None:
        c = etree.SubElement(rpr, q("color"))
    c.set(q("val"), val)
    for k in list(c.attrib):
        if k != q("val"):
            del c.attrib[k]


def set_highlight(r, val=TODO_HIGHLIGHT):
    rpr = ensure_rpr(r)
    h = rpr.find(q("highlight"))
    if val is None:
        if h is not None:
            rpr.remove(h)
        return
    if h is None:
        h = etree.SubElement(rpr, q("highlight"))
    h.set(q("val"), val)


def is_highlighted(r):
    h = r.find("w:rPr/w:highlight", NS)
    return h is not None and h.get(q("val")) == TODO_HIGHLIGHT


def set_run_text(r, text):
    ts = r.findall(q("t"))
    if not ts:
        t = etree.SubElement(r, q("t"))
        ts = [t]
    ts[0].text = text
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in ts[1:]:
        r.remove(t)


def make_run(text, like=None, highlight=False, bold=None):
    r = etree.Element(q("r"))
    if like is not None and like.find(q("rPr")) is not None:
        rpr = copy.deepcopy(like.find(q("rPr")))
        for tag in ("color", "highlight", "shd"):
            for x in rpr.findall(q(tag)):
                rpr.remove(x)
        r.append(rpr)
    t = etree.SubElement(r, q("t"))
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    if highlight:
        set_highlight(r)
    if bold is not None:
        rpr = ensure_rpr(r)
        for x in rpr.findall(q("b")):
            rpr.remove(x)
        if bold:
            etree.SubElement(rpr, q("b"))
    return r


def paragraph_runs(p):
    return [r for r in p.iter(q("r")) if r.getparent() is not None]


def set_paragraph_text(p, text, highlight=False, like=None):
    """把段落的全部文字换成 text，保留段落格式和第一个文字 run 的字体。"""
    runs = [r for r in p.findall(q("r"))] + [r for h in p.findall(q("hyperlink")) for r in h.findall(q("r"))]
    first = like
    if first is None:
        for r in runs:
            if run_text(r).strip():
                first = r
                break
    for r in runs:
        r.getparent().remove(r)
    if text:
        p.append(make_run(text, like=first, highlight=highlight))
    return p


def append_text(p, text, highlight=False, like=None):
    if like is None:
        rs = p.findall(q("r"))
        like = rs[-1] if rs else None
    p.append(make_run(text, like=like, highlight=highlight))


def replace_in_runs(el, old, new, highlight=False):
    """在 el 下逐个 run 替换文字。跨 run 的文字先合并同一段落再替换。返回替换次数。"""
    n = 0
    for p in el.iter(q("p")):
        full = "".join(run_text(r) for r in p.findall(q("r")))
        if old not in full:
            continue
        n += _replace_in_paragraph(p, old, new, highlight)
    return n


def _replace_in_paragraph(p, old, new, highlight):
    runs = p.findall(q("r"))
    texts = [run_text(r) for r in runs]
    full = "".join(texts)
    count = 0
    start = full.find(old)
    while start >= 0:
        end = start + len(old)
        pos = 0
        first_idx = None
        for i, t in enumerate(texts):
            a, b = pos, pos + len(t)
            if b <= start or a >= end:
                pos = b
                continue
            keep_before = t[: max(0, start - a)]
            keep_after = t[max(0, end - a):] if b > end else ""
            if first_idx is None:
                first_idx = i
                texts[i] = keep_before + new + keep_after
                set_run_text(runs[i], texts[i])
                if highlight:
                    set_highlight(runs[i])
            else:
                texts[i] = keep_after
                set_run_text(runs[i], texts[i])
            pos = b
        count += 1
        full = "".join(texts)
        start = full.find(old, start + len(new))
    return count


def deep(el):
    return copy.deepcopy(el)


def set_repeat_header(tbl, on=True):
    rows = rows_of(tbl)
    if not rows:
        return
    tr = rows[0]
    trpr = tr.find(q("trPr"))
    if trpr is None:
        trpr = etree.Element(q("trPr"))
        tr.insert(0 if tr.find(q("tblPrEx")) is None else 1, trpr)
    h = trpr.find(q("tblHeader"))
    if on and h is None:
        etree.SubElement(trpr, q("tblHeader"))
    if not on and h is not None:
        trpr.remove(h)


def empty_paragraph():
    return etree.Element(q("p"))


def page_break_paragraph():
    p = etree.Element(q("p"))
    r = etree.SubElement(p, q("r"))
    br = etree.SubElement(r, q("br"))
    br.set(q("type"), "page")
    return p


def has_sectpr(p):
    return p.find("w:pPr/w:sectPr", NS) is not None


def has_page_break(p):
    return any(b.get(q("type")) == "page" for b in p.iter(q("br")))


def paragraph(text, like_p=None, highlight=False, bold=None):
    p = deep(like_p) if like_p is not None else etree.Element(q("p"))
    like = None
    for r in p.iter(q("r")):
        if run_text(r).strip():
            like = r
            break
    for child in list(p):
        if child.tag != q("pPr"):
            p.remove(child)
    p.append(make_run(text, like=like, highlight=highlight, bold=bold))
    return p


def style_maps(styles_el):
    by_id, by_name = {}, {}
    for s in styles_el.findall(q("style")):
        sid = s.get(q("styleId"))
        n = s.find(q("name"))
        name = n.get(q("val")) if n is not None else sid
        by_id[sid] = name
        by_name.setdefault((s.get(q("type")), name), sid)
    return by_id, by_name


def remap_styles(el, src_styles, dst_styles):
    """把从别的文档拷来的元素里的样式 id 换成目标文档的同名样式，找不到就去掉。"""
    s_by_id, _ = style_maps(src_styles)
    _, d_by_name = style_maps(dst_styles)
    kinds = {"pStyle": "paragraph", "rStyle": "character", "tblStyle": "table"}
    for tag, kind in kinds.items():
        for x in el.iter(q(tag)):
            sid = x.get(q("val"))
            name = s_by_id.get(sid)
            target = d_by_name.get((kind, name)) if name else None
            if target is None and kind == "table":
                target = d_by_name.get(("table", "Table Grid")) or d_by_name.get(("table", "网格型"))
            if target:
                x.set(q("val"), target)
            else:
                x.getparent().remove(x)
    for x in list(el.iter(q("numPr"))):
        x.getparent().remove(x)
    for d in list(el.iter(q("drawing"))) + list(el.iter(q("object"))) + list(el.iter(q("pict"))):
        r = d.getparent()
        if r is None:
            continue
        idx = r.index(d)
        r.remove(d)
        t = etree.Element(q("t"))
        t.text = "【待补：图片】"
        r.insert(idx, t)
        set_highlight(r)
    for x in list(el.iter(q("commentRangeStart"))) + list(el.iter(q("commentRangeEnd"))):
        x.getparent().remove(x)
    for x in list(el.iter(q("commentReference"))):
        r = x.getparent()
        r.getparent().remove(r)
    for tag in ("ins", "del", "moveFrom", "moveTo"):
        for x in list(el.iter(q(tag))):
            parent = x.getparent()
            if tag in ("del", "moveFrom"):
                parent.remove(x)
            else:
                idx = parent.index(x)
                for child in list(x):
                    parent.insert(idx, child)
                    idx += 1
                parent.remove(x)
    for x in list(el.iter(q("delText"))):
        x.getparent().remove(x)
    strip_bookmarks(el)
    return el


_AFTER_UPDATE_FIELDS = ["hdrShapeDefaults", "footnotePr", "endnotePr", "compat", "docVars", "rsids", "mathPr",
                        "attachedSchema", "themeFontLang", "clrSchemeMapping", "doNotIncludeSubdocsInStats",
                        "doNotAutoCompressPictures", "forceUpgrade", "captions", "readModeInkLockDown", "smartTagType",
                        "schemaLibrary", "shapeDefaults", "doNotEmbedSmartTags", "decimalSymbol", "listSeparator"]


def set_update_fields(settings):
    """打开文档时更新目录和页码。按 schema 顺序插在 hdrShapeDefaults 等元素之前。"""
    if settings.find(q("updateFields")) is not None:
        return False
    uf = etree.Element(q("updateFields"))
    uf.set(q("val"), "true")
    for tag in _AFTER_UPDATE_FIELDS:
        x = settings.find(q(tag))
        if x is not None:
            x.addprevious(uf)
            return True
    settings.append(uf)
    return True


def strip_bookmarks(el):
    for tag in ("bookmarkStart", "bookmarkEnd"):
        for x in list(el.iter(q(tag))):
            x.getparent().remove(x)


def drop_blue_runs(el):
    """删掉蓝色说明文字。整段都是蓝字的段落直接删除。返回删除的段落数。"""
    removed = 0
    for p in list(el.iter(q("p"))):
        runs = [r for r in p.iter(q("r")) if run_text(r)]
        if not runs:
            continue
        blue = [r for r in runs if is_blue(r)]
        if not blue:
            continue
        if len(blue) == len([r for r in runs if run_text(r).strip()]) and not any(
            run_text(r).strip() for r in runs if r not in blue
        ):
            parent = p.getparent()
            if parent is not None and parent.tag == q("tc") and len(parent.findall(q("p"))) == 1:
                for r in blue:
                    r.getparent().remove(r)
            elif parent is not None and not has_sectpr(p):
                parent.remove(p)
                removed += 1
            else:
                for r in blue:
                    r.getparent().remove(r)
        else:
            for r in blue:
                r.getparent().remove(r)
    return removed


def pink_to_todo(el):
    """把剩下的粉色槽位改成黑字加黄色高亮，表示需要人工确认。"""
    n = 0
    for r in el.iter(q("r")):
        if is_pink(r) and run_text(r).strip():
            set_color(r, None)
            set_highlight(r)
            n += 1
        elif is_pink(r):
            set_color(r, None)
    return n


def pink_to_black(el):
    for r in el.iter(q("r")):
        if is_pink(r):
            set_color(r, None)


def strip_red(el):
    for r in el.iter(q("r")):
        if run_color(r) == "FF0000":
            set_color(r, None)
