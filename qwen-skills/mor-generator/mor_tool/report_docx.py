"""把报告写成 Word。报告先按简单的 markdown 组织（标题 #、表格 |、列表 -、加粗 **），这里转成 docx。"""

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

CN_FONT = "宋体"
EN_FONT = "Times New Roman"


def _set_fonts(style_or_run, size=None, bold=None):
    font = style_or_run.font
    font.name = EN_FONT
    if size:
        font.size = Pt(size)
    if bold is not None:
        font.bold = bold
    el = style_or_run.element
    rpr = el.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for k in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(k), EN_FONT)
    rfonts.set(qn("w:eastAsia"), CN_FONT)


def _inline(paragraph, text, size=None, bold=False):
    text = text.replace("`", "")
    for k, part in enumerate(re.split(r"\*\*", text)):
        if not part:
            continue
        r = paragraph.add_run(part)
        _set_fonts(r, size=size, bold=bold or k % 2 == 1)
        if "【待补" in part:
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return paragraph


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trpr.append(el)


def _table(doc, lines):
    rows = [_cells(x) for x in lines]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    if not rows:
        return
    n = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=n)
    t.style = "Table Grid"
    t.autofit = False

    def w(s):
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in s.replace("*", "").replace("`", ""))
    need = [max(4, min(40, max((w(r[j]) for r in rows if j < len(r)), default=4))) for j in range(n)]
    sec = doc.sections[-1]
    total = sec.page_width - sec.left_margin - sec.right_margin
    widths = [int(total * x / sum(need)) for x in need]
    for col, width in zip(t.columns, widths):
        col.width = width
    for i, r in enumerate(rows):
        row = t.add_row()
        for j in range(n):
            cell = row.cells[j]
            cell.width = widths[j]
            cell.paragraphs[0].text = ""
            _inline(cell.paragraphs[0], r[j] if j < len(r) else "", size=9, bold=(i == 0))
        if i == 0:
            _repeat_header(row)
            for cell in row.cells:
                tcpr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "D9E2F3")
                tcpr.append(shd)
    doc.add_paragraph()


def md_to_docx(md, out_path, landscape=False):
    doc = Document()
    sec = doc.sections[0]
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2))
    _set_fonts(doc.styles["Normal"], size=10.5)
    for name, size in (("Title", 18), ("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 11)):
        st = doc.styles[name]
        _set_fonts(st, size=size, bold=True)
        st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x60)
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            _table(doc, block)
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            h = doc.add_heading(level=0 if level == 1 else level - 1)
            _inline(h, m.group(2))
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x60)
        elif re.match(r"^[-*]\s+", s):
            _inline(doc.add_paragraph(style="List Bullet"), re.sub(r"^[-*]\s+", "", s))
        else:
            _inline(doc.add_paragraph(), s)
        i += 1
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


def write_report(md, out_path, landscape=False):
    """按扩展名输出：.md 写文本，其他写 Word。默认用 Word。"""
    out_path = Path(out_path)
    if out_path.suffix.lower() == ".md":
        out_path.write_text(md, encoding="utf-8")
        return out_path
    if out_path.suffix.lower() != ".docx":
        out_path = out_path.with_name(out_path.name + ".docx")
    return md_to_docx(md, out_path, landscape=landscape)
