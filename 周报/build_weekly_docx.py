"""把周报 Markdown 转成 Word。

用法：python 周报/build_weekly_docx.py 周报/2026-11-06_AI工作周报.md
输出：同目录、同名的 .docx
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = "0F1F3D"
ORANGE = "FF7E3D"
BLUE = "1E40AF"
TEXT = "1F2A44"
GREY = "5B6A8A"
FONT = "Microsoft YaHei"
CONTENT_CM = 17.0

PPR_AFTER_SHD = ("w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                 "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
                 "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
                 "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
                 "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")
LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


# ---------- 解析 ----------

def parse(md):
    lines, blocks, i = md.splitlines(), [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or re.fullmatch(r"-{3,}", s):
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m:
            blocks.append((f"h{len(m.group(1))}", m.group(2)))
            i += 1
            continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(("quote", " ".join(buf)))
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in row):
                    rows.append(row)
                i += 1
            blocks.append(("table", rows))
            continue
        if LIST_RE.match(lines[i]):
            items = []
            while i < len(lines) and LIST_RE.match(lines[i]):
                ind, marker, text = LIST_RE.match(lines[i]).groups()
                items.append((min(len(ind) // 2, 2), None if marker in "-*" else marker, text))
                i += 1
            blocks.append(("list", items))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|\||-{3,}$)", lines[i].strip()) \
                and not LIST_RE.match(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(("p", "".join(buf)))
    return blocks


def inline_parts(text):
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**"):
            out.append((part[2:-2], "b"))
        elif part.startswith("`"):
            out.append((part[1:-1], "code"))
        else:
            out.append((part, None))
    return out


# ---------- Word 工具 ----------

def font(run, size=10.5, bold=None, color=TEXT, mono=False):
    name = "Consolas" if mono else FONT
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), name)
    rf.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_inline(par, text, size=10.5, color=TEXT, bold=False):
    for t, style in inline_parts(text):
        r = par.add_run(t)
        font(r, size=size, bold=bold or style == "b", color=(BLUE if style == "code" else color),
             mono=(style == "code"))


def shade_cell(cell, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    cell._element.get_or_add_tcPr().append(shd)


def para_left_border(par, color=ORANGE, size="24"):
    bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    for k, v in (("w:val", "single"), ("w:sz", size), ("w:space", "8"), ("w:color", color)):
        left.set(qn(k), v)
    bdr.append(left)
    par._element.get_or_add_pPr().insert_element_before(bdr, "w:shd", *PPR_AFTER_SHD)


def para_shade(par, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    par._element.get_or_add_pPr().insert_element_before(shd, *PPR_AFTER_SHD)


def page_number(par):
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        r = par.add_run()
        font(r, size=9, color="7A869E")
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._element.append(fc)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            r._element.append(it)


def col_widths(rows):
    lens = []
    for c in range(len(rows[0])):
        m = max(len(r[c]) if c < len(r) else 0 for r in rows)
        lens.append(min(max(m, 3 if rows[0][c] == "#" else 6), 40))
    s = sum(lens)
    return [CONTENT_CM * x / s for x in lens]


# ---------- 生成 ----------

def build(src: Path):
    blocks = parse(src.read_text(encoding="utf-8"))
    doc = Document()
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    title = next((v for k, v in blocks if k == "h1"), src.stem)
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    font(hp.add_run(title), size=8.5, color="7A869E")
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    page_number(fp)

    after_h1 = False
    for kind, val in blocks:
        if kind == "h1":
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            font(p.add_run(val), size=18, bold=True, color=NAVY)
            after_h1 = True
            continue
        if kind == "h2":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            para_left_border(p)
            font(p.add_run(val), size=13.5, bold=True, color=NAVY)
        elif kind == "h3":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            add_inline(p, val, size=11.5, color=BLUE, bold=True)
        elif kind == "p":
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.3
            if after_h1:
                add_inline(p, val, size=10, color=GREY)
                p.paragraph_format.space_after = Pt(8)
            else:
                add_inline(p, val)
                if re.fullmatch(r"\*\*[^*]+\*\*", val):
                    p.paragraph_format.keep_with_next = True
        elif kind == "quote":
            p = doc.add_paragraph()
            para_shade(p, "F3F5FA")
            para_left_border(p, color="9AA7C2", size="18")
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(6)
            add_inline(p, val, size=9.5, color=GREY)
        elif kind == "list":
            for level, num, text in val:
                p = doc.add_paragraph(style=None if num else ("List Bullet 2" if level else "List Bullet"))
                pf = p.paragraph_format
                pf.space_after = Pt(2)
                pf.line_spacing = 1.25
                if num:
                    pf.left_indent = Cm(0.75 + 0.75 * level)
                    pf.first_line_indent = Cm(-0.5)
                    r = p.add_run(f"{num} ")
                    font(r, color=TEXT)
                add_inline(p, text)
        elif kind == "table":
            add_table(doc, val)
        after_h1 = after_h1 and kind == "h1"

    out = src.with_suffix(".docx")
    doc.save(out)
    return out


def add_table(doc, rows):
    ncol = len(rows[0])
    tbl = doc.add_table(rows=len(rows), cols=ncol)
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = col_widths(rows)
    for r, row in enumerate(rows):
        trpr = tbl.rows[r]._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        if r == 0:
            h = OxmlElement("w:tblHeader")
            h.set(qn("w:val"), "true")
            trpr.append(h)
        for c in range(ncol):
            cell = tbl.cell(r, c)
            cell.width = Cm(widths[c])
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            text = row[c] if c < len(row) else ""
            if r == 0:
                shade_cell(cell, NAVY)
                font(p.add_run(text), size=9.5, bold=True, color="FFFFFF")
            else:
                if r % 2 == 0:
                    shade_cell(cell, "F7F9FC")
                add_inline(p, text, size=9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print("已生成：", build(Path(sys.argv[1])))
