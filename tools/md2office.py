"""把 Markdown 方案文档转成 Word 和 HTML（同目录、同名）。

用法：python tools/md2office.py <文件.md> [--docx-only | --html-only]
支持：# ## ### 标题、段落、引用块、表格、有序/无序（含二级）列表、代码块、**粗体**、`代码`。
HTML 中代码块带"复制"按钮，适合放提示词。
"""
import html
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY, ORANGE, BLUE, TEXT, GREY = "0F1F3D", "FF7E3D", "1E40AF", "1F2A44", "5B6A8A"
FONT = "Microsoft YaHei"
CONTENT_CM = 17.0
LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")
PPR_AFTER_SHD = ("w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                 "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
                 "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
                 "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
                 "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")


# ---------- 解析 ----------

def parse(md):
    lines, blocks, i = md.splitlines(), [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or re.fullmatch(r"-{3,}", s):
            i += 1
            continue
        if s.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            blocks.append(("code", lines[i + 1:j]))
            i = j + 1
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
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|\||```|-{3,}$)", lines[i].strip()) \
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


# ---------- Word ----------

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
        font(par.add_run(t), size=size, bold=bold or style == "b",
             color=(BLUE if style == "code" else color), mono=(style == "code"))


def shade_cell(cell, fill):
    shd = OxmlElement("w:shd")
    for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", fill)):
        shd.set(qn(k), v)
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
    for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", fill)):
        shd.set(qn(k), v)
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


def add_table(doc, rows):
    ncol = len(rows[0])
    tbl = doc.add_table(rows=len(rows), cols=ncol)
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = col_widths(rows)
    size = 9 if ncol >= 6 else 9.5
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
                font(p.add_run(text), size=size, bold=True, color="FFFFFF")
            else:
                if r % 2 == 0:
                    shade_cell(cell, "F7F9FC")
                add_inline(p, text, size=size)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def build_docx(blocks, out):
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

    title = next((v for k, v in blocks if k == "h1"), out.stem)
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
            font(p.add_run(val), size=17, bold=True, color=NAVY)
            after_h1 = True
            continue
        if kind == "h2":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.outline_level = 0
            para_left_border(p)
            font(p.add_run(val), size=13.5, bold=True, color=NAVY)
        elif kind == "h3":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.outline_level = 1
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
                if re.fullmatch(r"\*\*[^*]+\*\*：?", val):
                    p.paragraph_format.keep_with_next = True
        elif kind == "quote":
            p = doc.add_paragraph()
            para_shade(p, "FFF7F1")
            para_left_border(p)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(6)
            add_inline(p, val, size=10, color="3A4D72")
        elif kind == "list":
            for level, num, text in val:
                p = doc.add_paragraph(style=None if num else ("List Bullet 2" if level else "List Bullet"))
                pf = p.paragraph_format
                pf.space_after = Pt(2)
                pf.line_spacing = 1.25
                if num:
                    pf.left_indent = Cm(0.75 + 0.75 * level)
                    pf.first_line_indent = Cm(-0.5)
                    font(p.add_run(f"{num} "))
                add_inline(p, text)
        elif kind == "code":
            for n, line in enumerate(val or [""]):
                p = doc.add_paragraph()
                para_shade(p, "F3F5FA")
                pf = p.paragraph_format
                pf.space_after = Pt(0)
                pf.space_before = Pt(4) if n == 0 else Pt(0)
                pf.line_spacing = 1.15
                pf.left_indent = Cm(0.2)
                font(p.add_run(line if line else " "), size=8.5, color="1F2A44", mono=True)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        elif kind == "table":
            add_table(doc, val)
        after_h1 = after_h1 and kind == "h1"
    doc.save(out)


# ---------- HTML ----------

def inline_html(text):
    out = []
    for t, style in inline_parts(text):
        e = html.escape(t)
        out.append(f"<strong>{e}</strong>" if style == "b" else f"<code>{e}</code>" if style == "code" else e)
    return "".join(out)


def list_html(items):
    out, open_sub = ["<ul class=\"bul\">"], False
    for level, num, text in items:
        cls = "sub" if level else ""
        prefix = f"<span class=\"num\">{html.escape(num)}</span> " if num else ""
        out.append(f'<li class="{cls}{" numbered" if num else ""}">{prefix}{inline_html(text)}</li>')
    out.append("</ul>")
    return "".join(out)


def build_html(blocks, out):
    title = next((v for k, v in blocks if k == "h1"), out.stem)
    nav, body, sec_open, n = [], [], False, 0
    for kind, val in blocks:
        if kind == "h1":
            body.append(f'<header class="cover"><h1>{inline_html(val)}</h1>')
            continue
        if kind == "h2":
            if body and body[0].startswith('<header') and not sec_open and "</header>" not in "".join(body):
                body.append("</header>")
            if sec_open:
                body.append("</section>")
            n += 1
            sid = f"s{n}"
            short = re.sub(r"^[一二三四五六七八九十]+、", "", val)
            short = re.split(r"[（(：]", short)[0].strip()
            nav.append(f'<a href="#{sid}">{html.escape(short)}</a>')
            body.append(f'<section class="card" id="{sid}"><h2>{inline_html(val)}</h2>')
            sec_open = True
        elif kind == "h3":
            body.append(f"<h3>{inline_html(val)}</h3>")
        elif kind == "p":
            body.append(f'<p class="{"meta" if not sec_open else ""}">{inline_html(val)}</p>')
        elif kind == "quote":
            body.append(f'<div class="quote">{inline_html(val)}</div>')
        elif kind == "list":
            body.append(list_html(val))
        elif kind == "code":
            code = html.escape("\n".join(val))
            body.append(f'<div class="code"><button onclick="copyCode(this)">复制</button><pre>{code}</pre></div>')
        elif kind == "table":
            head = "".join(f"<th>{inline_html(c)}</th>" for c in val[0])
            rows = "".join("<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in r) + "</tr>" for r in val[1:])
            body.append(f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')
    if sec_open:
        body.append("</section>")
    out.write_text(HTML_TPL.format(title=html.escape(title), nav="".join(nav), body="".join(body)), encoding="utf-8")


HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"PingFang SC","Microsoft YaHei","Source Han Sans CN",sans-serif; color:#0f1f3d;
         background:#f3f5fa; line-height:1.75; }}
  .topbar {{ position:sticky; top:0; z-index:50; display:flex; gap:4px; align-items:center; flex-wrap:wrap;
            padding:8px 24px; background:rgba(15,31,61,.96); box-shadow:0 2px 10px rgba(0,0,0,.15); }}
  .topbar a {{ color:#cdd6e8; font-size:12.5px; text-decoration:none; padding:5px 10px; border-radius:6px; }}
  .topbar a:hover {{ background:#1d2f55; color:#fff; }}
  main {{ max-width:1180px; margin:0 auto; padding:0 24px 80px; }}
  header.cover {{ margin:24px 0; padding:36px 44px; border-radius:14px; color:#fff;
                 background:linear-gradient(135deg,#0f1f3d 0%,#1f3870 60%,#2a4d9c 100%); }}
  header.cover h1 {{ margin:0 0 8px; font-size:28px; }}
  header.cover p {{ color:#dbe3f3; margin:6px 0; font-size:14px; }}
  header.cover .quote {{ background:rgba(255,255,255,.1); color:#eef2fa; border-left-color:#ff7e3d; }}
  section.card {{ background:#fff; border-radius:14px; padding:32px 44px 36px; margin:22px 0;
                 box-shadow:0 6px 24px rgba(15,31,61,.07); }}
  h2 {{ font-size:22px; margin:0 0 16px; border-left:5px solid #ff7e3d; padding-left:12px; }}
  h3 {{ font-size:16px; color:#1e40af; margin:22px 0 8px; }}
  p {{ font-size:14px; color:#3a4d72; margin:8px 0; }}
  code {{ background:#eef2fb; color:#1e40af; padding:1px 6px; border-radius:4px; font-size:12.5px; }}
  .quote {{ background:#fff7f1; border-left:4px solid #ff7e3d; padding:12px 18px; margin:12px 0;
           border-radius:0 8px 8px 0; color:#3a4d72; font-size:14px; }}
  .tbl {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin:10px 0 16px; }}
  th, td {{ padding:8px 11px; text-align:left; border-bottom:1px solid #e6ebf5; vertical-align:top; line-height:1.65; }}
  thead th {{ background:#0f1f3d; color:#fff; font-weight:600; font-size:12px; white-space:nowrap; }}
  tbody tr:nth-child(even) {{ background:#f7f9fc; }}
  ul.bul {{ list-style:none; padding-left:0; margin:6px 0; }}
  ul.bul li {{ position:relative; padding:3px 0 3px 22px; font-size:14px; color:#3a4d72; }}
  ul.bul li:before {{ content:""; position:absolute; left:4px; top:13px; width:7px; height:7px; background:#ff7e3d;
                     border-radius:2px; transform:rotate(45deg); }}
  ul.bul li.numbered:before {{ display:none; }}
  ul.bul li.numbered {{ padding-left:4px; }}
  ul.bul li .num {{ color:#ff7e3d; font-weight:700; }}
  ul.bul li.sub {{ margin-left:24px; font-size:13.5px; }}
  ul.bul li.sub:before {{ width:5px; height:5px; background:#9aa7c2; top:14px; }}
  .code {{ position:relative; margin:10px 0 16px; }}
  .code pre {{ background:#0f1f3d; color:#e6ecf7; padding:16px 18px; border-radius:10px; font-size:12.5px;
              line-height:1.6; white-space:pre-wrap; word-break:break-word; margin:0;
              font-family:Consolas,"Microsoft YaHei",monospace; }}
  .code button {{ position:absolute; top:8px; right:8px; background:#ff7e3d; color:#fff; border:none;
                 border-radius:6px; padding:4px 12px; font-size:12px; cursor:pointer; }}
  @media print {{ .topbar, .code button {{ display:none; }} body {{ background:#fff; }}
                 section.card {{ box-shadow:none; }} }}
</style></head>
<body>
<div class="topbar">{nav}</div>
<main>{body}</main>
<script>
function copyCode(btn) {{
  const text = btn.nextElementSibling.innerText;
  navigator.clipboard.writeText(text).then(() => {{ btn.textContent = "已复制"; setTimeout(() => btn.textContent = "复制", 1500); }});
}}
</script>
</body></html>
"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    blocks = parse(src.read_text(encoding="utf-8"))
    made = []
    if "--html-only" not in sys.argv:
        build_docx(blocks, src.with_suffix(".docx"))
        made.append(src.with_suffix(".docx").name)
    if "--docx-only" not in sys.argv:
        build_html(blocks, src.with_suffix(".html"))
        made.append(src.with_suffix(".html").name)
    print("已生成：", "、".join(made))
