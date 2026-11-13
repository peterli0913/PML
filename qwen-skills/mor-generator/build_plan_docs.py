"""把 PLAN.md 转成 Word（MOR_实施计划.docx）和 HTML（MOR_实施计划.html）。

用法：python build_plan_docs.py              # 同时生成 Word 和 HTML（会覆盖已有 Word）
      python build_plan_docs.py --html-only  # 只更新 HTML，保留手工修改过的 Word
"""
import html
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).parent
SRC = HERE / "PLAN.md"
OUT_DOCX = HERE / "MOR_实施计划.docx"
OUT_HTML = HERE / "MOR_实施计划.html"

TITLE = "MOR 生成工具 · 实施计划"
SUBTITLE = "从原料药工艺到 MOR 草稿：拆零件、AI 拼装与核对、专家批注持续沉淀"
NAVY = "0F1F3D"
ORANGE = "FF7E3D"
FONT = "Microsoft YaHei"

NAV_SHORT = {"先用 skill + 钉钉文档": "先 skill 后小程序"}

FLOW_STEPS = [
    ("工艺文件", ""),
    ("① 解析", "AI"),
    ("结构化工艺步骤表", ""),
    ("② 人工确认", "MOR 编写人"),
    ("③ 组装", "模板为主 · AI 为辅"),
    ("MOR 草稿", ""),
    ("④ 自动核对", "程序"),
    ("专家审改", ""),
    ("⑤ 批注沉淀", "回流规则 / 模板"),
]


# ---------- Markdown 解析 ----------

def parse(md: str):
    lines = md.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            blocks.append(("code", "\n".join(lines[i + 1:j])))
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
        if s.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                level = 1 if len(lines[i]) - len(lines[i].lstrip()) >= 2 else 0
                items.append((level, lines[i].strip()[2:]))
                i += 1
            blocks.append(("ul", items))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|\||- |```)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(("p", "".join(buf)))
    return blocks


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def inline_parts(text):
    """拆成 [(文本, 样式)]，样式为 None / 'b' / 'code'。"""
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

def set_run_font(run, size=None, bold=None, color=None, mono=False):
    font = "Consolas" if mono else FONT
    run.font.name = font
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT if attr == "w:eastAsia" else font)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_inline(par, text, size=10.5, color=None, bold=False):
    for t, style in inline_parts(text):
        r = par.add_run(t)
        set_run_font(r, size=size, bold=bold or style == "b",
                     color=(ORANGE if style == "code" else color), mono=False)


def shade(cell, fill):
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


PPR_AFTER_SHD = ("w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                 "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
                 "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
                 "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
                 "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")


def para_border_left(par, color=ORANGE):
    ppr = par._element.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "24")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), color)
    bdr.append(left)
    ppr.insert_element_before(bdr, "w:shd", *PPR_AFTER_SHD)


def para_shading(par, fill):
    ppr = par._element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.insert_element_before(shd, *PPR_AFTER_SHD)


def add_page_number(par):
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        r = par.add_run()
        set_run_font(r, size=9, color="7A869E")
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._element.append(fc)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            r._element.append(it)


def col_widths(rows, total_cm):
    lens = []
    for c in range(len(rows[0])):
        m = max(len(r[c]) if c < len(r) else 0 for r in rows)
        floor = 3 if rows[0][c] == "#" else 8
        lens.append(min(max(m, floor), 40))
    s = sum(lens)
    return [total_cm * l / s for l in lens]


def build_docx(blocks):
    doc = Document()
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(2)
    content_cm = 17

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_run_font(hp.add_run(TITLE), size=8.5, color="7A869E")
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number(fp)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    set_run_font(p.add_run(TITLE), size=22, bold=True, color=NAVY)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    set_run_font(p.add_run(SUBTITLE), size=11, color="5B6A8A")

    for kind, val in blocks:
        if kind == "h1":
            continue
        if kind == "h2":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.outline_level = 0
            para_border_left(p)
            set_run_font(p.add_run(val), size=15, bold=True, color=NAVY)
        elif kind == "h3":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.outline_level = 1
            set_run_font(p.add_run(val), size=12, bold=True, color="1E40AF")
        elif kind == "quote":
            p = doc.add_paragraph()
            para_shading(p, "FFF7F1")
            para_border_left(p)
            p.paragraph_format.space_after = Pt(8)
            add_inline(p, val, size=10, color="3A4D72")
        elif kind == "p":
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.35
            add_inline(p, val, color="1F2A44")
        elif kind == "ul":
            for level, item in val:
                p = doc.add_paragraph(style="List Bullet 2" if level else "List Bullet")
                p.paragraph_format.space_after = Pt(3)
                add_inline(p, item, color="1F2A44")
        elif kind == "code":
            if "①" in val:
                build_docx_flow(doc, content_cm)
            else:
                p = doc.add_paragraph()
                para_shading(p, "F3F5FA")
                set_run_font(p.add_run(val), size=9, mono=True)
        elif kind == "table":
            build_docx_table(doc, val, content_cm)
    doc.save(OUT_DOCX)


def build_docx_flow(doc, content_cm):
    tbl = doc.add_table(rows=2, cols=len(FLOW_STEPS))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblpr = tbl._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), "30")
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription", "w:tblPrChange")
    w = Cm(content_cm / len(FLOW_STEPS))
    for c, (name, who) in enumerate(FLOW_STEPS):
        is_step = name[0] in "①②③④⑤"
        for r, text in enumerate((name, who)):
            cell = tbl.cell(r, c)
            cell.width = w
            shade(cell, (NAVY if is_step else "EFF3FA") if r == 0 else "FFFFFF")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(p.add_run(text), size=7.5 if r == 0 else 6.5,
                         bold=(r == 0), color=("FFFFFF" if (is_step and r == 0) else "3A4D72"))
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    set_run_font(p.add_run("⑤ 专家批注沉淀为规则 / 模板，回流到解析与组装环节，工具越用越准。"),
                 size=9, color="5B6A8A")


def build_docx_table(doc, rows, content_cm):
    ncol = len(rows[0])
    tbl = doc.add_table(rows=len(rows), cols=ncol)
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = col_widths(rows, content_cm)
    for r, row in enumerate(rows):
        for c in range(ncol):
            cell = tbl.cell(r, c)
            cell.width = Cm(widths[c])
            text = row[c] if c < len(row) else ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            if r == 0:
                shade(cell, NAVY)
                set_run_font(p.add_run(text), size=9.5, bold=True, color="FFFFFF")
            else:
                if r % 2 == 0:
                    shade(cell, "F7F9FC")
                add_inline(p, text, size=9.5, color="1F2A44")
    for idx, row in enumerate(tbl.rows):
        trpr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        if idx == 0:
            hdr = OxmlElement("w:tblHeader")
            hdr.set(qn("w:val"), "true")
            trpr.append(hdr)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ---------- HTML ----------

def inline_html(text):
    out = []
    for t, style in inline_parts(text):
        e = html.escape(t)
        out.append(f"<strong>{e}</strong>" if style == "b" else f"<code>{e}</code>" if style == "code" else e)
    return "".join(out)


def build_html(blocks):
    sections, cur = [], None
    for kind, val in blocks:
        if kind == "h1":
            continue
        if kind == "h2":
            cur = {"title": val, "body": []}
            sections.append(cur)
            continue
        if cur is None:
            cur = {"title": None, "body": []}
            sections.append(cur)
        cur["body"].append((kind, val))

    nav, parts = [], []
    for idx, s in enumerate(sections):
        sid = f"s{idx}"
        body = []
        for kind, val in s["body"]:
            if kind == "h3":
                body.append(f"<h3>{inline_html(val)}</h3>")
            elif kind == "p":
                body.append(f"<p>{inline_html(val)}</p>")
            elif kind == "quote":
                body.append(f'<div class="highlight-box">{inline_html(val)}</div>')
            elif kind == "ul":
                body.append('<ul class="bul">' + "".join(
                    f'<li class="{"sub" if lv else ""}">{inline_html(x)}</li>' for lv, x in val) + "</ul>")
            elif kind == "code":
                body.append(flow_html() if "①" in val else f"<pre>{html.escape(val)}</pre>")
            elif kind == "table":
                head = "".join(f"<th>{inline_html(c)}</th>" for c in val[0])
                rows = "".join("<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in r) + "</tr>" for r in val[1:])
                body.append(f'<table class="kly"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>')
        if s["title"]:
            short = re.sub(r"^[一二三四五六七八九十]+、", "", s["title"])
            short = re.split(r"[：（，/]", short)[0].strip()
            short = NAV_SHORT.get(short, short)
            nav.append(f'<a href="#{sid}">{html.escape(short)}</a>')
            m = re.match(r"^([一二三四五六七八九十]+)、(.*)", s["title"])
            kicker = f"PART {['一','二','三','四','五','六','七','八','九','十'].index(m.group(1)[0]) + 1:02d}" if m else ""
            title = m.group(2) if m else s["title"]
            parts.append(f'<section class="slide" id="{sid}"><h2 class="kicker">{kicker}</h2>'
                         f"<h1>{inline_html(title)}</h1>{''.join(body)}</section>")
        else:
            parts.append(f'<section class="slide cover" id="cover"><h2 class="kicker">MOR GENERATOR · IMPLEMENTATION PLAN</h2>'
                         f"<h1>{html.escape(TITLE)}</h1><div class=\"subtitle\">{html.escape(SUBTITLE)}</div>"
                         f"{''.join(body)}</section>")

    OUT_HTML.write_text(HTML_TPL.format(title=html.escape(TITLE), nav="".join(nav), body="".join(parts)),
                        encoding="utf-8")


def flow_html():
    items = []
    for n, (name, who) in enumerate(FLOW_STEPS):
        cls = "step" if name[0] in "①②③④⑤" else "node"
        sub = f"<small>{html.escape(who)}</small>" if who else ""
        items.append(f'<div class="{cls}">{html.escape(name)}{sub}</div>')
        if n < len(FLOW_STEPS) - 1:
            items.append('<div class="arrow">→</div>')
    return ('<div class="flow">' + "".join(items) + "</div>"
            '<p class="flow-note">⑤ 专家批注沉淀为规则 / 模板，回流到解析与组装环节，工具越用越准。</p>')


HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin:0; padding:0; }}
  body {{ font-family: "PingFang SC","Microsoft YaHei","Source Han Sans CN","Noto Sans CJK SC",sans-serif;
         color:#0f1f3d; background:#f3f5fa; line-height:1.75; -webkit-font-smoothing:antialiased; }}
  .topbar {{ position:sticky; top:0; z-index:50; display:flex; align-items:center; justify-content:space-between;
            padding:10px 28px; background:rgba(15,31,61,.96); color:#fff; box-shadow:0 2px 10px rgba(0,0,0,.15); }}
  .topbar .brand {{ font-weight:700; font-size:14px; letter-spacing:.5px; }}
  .topbar .brand .badge {{ display:inline-block; padding:2px 8px; margin-left:8px; background:#ff7e3d;
                          border-radius:4px; font-size:11px; }}
  .topbar nav a {{ color:#cdd6e8; font-size:12.5px; text-decoration:none; margin:0 4px; padding:6px 10px; border-radius:6px; }}
  .topbar nav a:hover {{ background:#1d2f55; color:#fff; }}
  main {{ max-width:1100px; margin:0 auto; padding:0 24px 80px; }}
  section.slide {{ background:#fff; border-radius:14px; padding:40px 52px 44px; margin:24px 0;
                  box-shadow:0 6px 24px rgba(15,31,61,.07); }}
  section.slide.cover {{ background:linear-gradient(135deg,#0f1f3d 0%,#1f3870 60%,#2a4d9c 100%); color:#fff; }}
  section.slide.cover h1 {{ border:none; padding:0; font-size:34px; color:#fff; }}
  section.slide.cover .subtitle {{ font-size:16px; opacity:.88; margin-top:10px; }}
  section.slide.cover .highlight-box {{ background:rgba(255,255,255,.1); color:#e6ecf7; margin-top:24px; }}
  h2.kicker {{ color:#ff7e3d; font-size:12.5px; font-weight:700; letter-spacing:3px; margin:0 0 6px; }}
  section.slide h1 {{ font-size:24px; margin:0 0 18px; border-left:5px solid #ff7e3d; padding-left:14px; line-height:1.35; }}
  section.slide h3 {{ font-size:16px; color:#1e40af; margin:22px 0 10px; }}
  section.slide p {{ font-size:14px; color:#3a4d72; margin:8px 0; }}
  code {{ background:#fff3ea; color:#c2410c; padding:1px 6px; border-radius:4px; font-size:12.5px; }}
  pre {{ background:#f3f5fa; padding:14px 18px; border-radius:8px; font-size:12.5px; overflow-x:auto; }}
  table.kly {{ width:100%; border-collapse:collapse; font-size:13px; margin:10px 0 16px; }}
  table.kly th, table.kly td {{ padding:9px 12px; text-align:left; border-bottom:1px solid #e6ebf5; vertical-align:top; line-height:1.7; }}
  table.kly thead th {{ background:#0f1f3d; color:#fff; font-weight:600; font-size:12px; }}
  table.kly tbody tr:nth-child(even) {{ background:#f7f9fc; }}
  ul.bul {{ padding-left:0; list-style:none; margin:6px 0; }}
  ul.bul li {{ padding:4px 0 4px 22px; position:relative; font-size:14px; color:#3a4d72; }}
  ul.bul li:before {{ content:""; position:absolute; left:4px; top:14px; width:7px; height:7px; background:#ff7e3d;
                     border-radius:2px; transform:rotate(45deg); }}
  ul.bul li.sub {{ margin-left:24px; padding-left:18px; font-size:13.5px; }}
  ul.bul li.sub:before {{ width:5px; height:5px; background:#9aa7c2; top:15px; }}
  .highlight-box {{ background:#fff7f1; border-left:4px solid #ff7e3d; padding:14px 20px; margin:14px 0;
                   border-radius:0 8px 8px 0; color:#3a4d72; font-size:14px; }}
  .flow {{ display:flex; flex-wrap:nowrap; align-items:stretch; gap:4px; margin:14px 0 6px; }}
  .flow .node, .flow .step {{ padding:10px 6px; border-radius:8px; font-size:12.5px; font-weight:600; text-align:center;
                             display:flex; flex-direction:column; justify-content:center; flex:1 1 0; min-width:0; }}
  .flow .node {{ background:#eff3fa; color:#0f1f3d; border:1px solid #d7deec; }}
  .flow .step {{ background:#0f1f3d; color:#fff; }}
  .flow small {{ font-weight:400; font-size:11px; opacity:.8; margin-top:2px; }}
  .flow .arrow {{ display:flex; align-items:center; color:#ff7e3d; font-weight:700; }}
  .flow-note {{ font-size:12.5px !important; color:#5b6a8a !important; }}
  @media print {{ body {{ background:#fff; }} .topbar {{ display:none; }}
                 section.slide {{ box-shadow:none; page-break-inside:avoid; }} }}
</style>
</head>
<body>
<div class="topbar"><div class="brand">{title}<span class="badge">v0.1</span></div><nav>{nav}</nav></div>
<main>{body}</main>
</body>
</html>
"""


if __name__ == "__main__":
    blocks = parse(SRC.read_text(encoding="utf-8"))
    if "--html-only" not in sys.argv:
        build_docx(blocks)
    build_html(blocks)
    print("已生成：" + ("" if "--html-only" in sys.argv else f"{OUT_DOCX.name}、") + OUT_HTML.name)
