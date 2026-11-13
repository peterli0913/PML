"""单元操作库：按标题切成模块，记录大类、工况标签和粉色槽位。

模块 = 一个标题（1 级或 2 级）到下一个标题之间的表格和非空段落。
标题前带「#」的是同一工况的另一种写法，作为备选模块保留。
"""

import hashlib
import json
import re
import zipfile

from lxml import etree

from .ooxml import NS, clean, is_pink, q, run_text, text_of

TAG_WORDS = {
    "类GMP": ["类GMP"],
    "GMP": ["（GMP）", "(GMP)"],
    "商业化": ["商业化"],
    "非商业化": ["非商业化"],
    "打印DCS": ["打印DCS", "打DCS", "打印 DSC", "打印DSC", "打印 DCS"],
    "控温": ["控温"],
    "分批": ["分批"],
    "一次性": ["一次性"],
    "固体": ["固体"],
    "液体": ["液体", "Add liquid"],
    "水": ["加水", "Add water", "纯化水"],
    "无机盐": ["无机盐"],
    "折算": ["折算"],
    "KF": ["KF"],
    "体积选择": ["体积选择"],
    "补加": ["需补加"],
    "不补加": ["不需补加"],
    "淋洗": ["淋洗一次", "淋洗N次", "每锅淋洗", "继续淋洗", "溶液淋洗", "釜里预冷"],
    "不淋洗": ["不用淋洗"],
    "单次": ["（单次）", "(单次)"],
    "分锅": ["分锅"],
    "备选写法": ["#"],
}


def _style(p):
    s = p.find("w:pPr/w:pStyle", NS)
    return s.get("{%s}val" % NS["w"]) if s is not None else ""


def _heading_level(p, heading_ids):
    sid = _style(p)
    return heading_ids.get(sid)


def load(path):
    z = zipfile.ZipFile(str(path))
    root = etree.fromstring(z.read("word/document.xml"))
    styles = etree.fromstring(z.read("word/styles.xml"))
    return z, root, styles


def heading_style_ids(styles):
    out = {}
    for s in styles.findall("w:style", NS):
        n = s.find("w:name", NS)
        name = (n.get("{%s}val" % NS["w"]) if n is not None else "").lower()
        m = re.match(r"heading (\d)", name)
        if m:
            out[s.get("{%s}styleId" % NS["w"])] = int(m.group(1))
    return out


def build_index(path):
    _, root, styles = load(path)
    body = root.find("w:body", NS)
    els = list(body)
    hid = heading_style_ids(styles)
    heads = []
    for i, el in enumerate(els):
        if el.tag == q("p"):
            lvl = _heading_level(el, hid)
            t = clean(text_of(el))
            if lvl in (1, 2) and t:
                heads.append((i, lvl, t))
    modules = []
    family = ""
    for k, (i, lvl, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(els)
        if lvl == 1:
            family = title
        content = [j for j in range(i + 1, end) if els[j].tag == q("tbl") or (els[j].tag == q("p") and clean(text_of(els[j])))]
        tables = [j for j in content if els[j].tag == q("tbl")]
        if not tables:
            continue
        slots = []
        for j in content:
            for r in els[j].iter(q("r")):
                if is_pink(r) and run_text(r).strip():
                    slots.append(clean(run_text(r)))
        first_rows = []
        for j in tables[:1]:
            rows = els[j].findall(q("tr"))
            first_rows = [clean(text_of(r))[:120] for r in rows[:4]]
        tags = [t for t, words in TAG_WORDS.items() if any(w in title for w in words)]
        if title.startswith("#"):
            tags.append("备选写法")
        if "不需补加" in title and "补加" in tags:
            tags.remove("补加")
        ins_title = ""
        for row in first_rows:
            m = re.search(r"Ins\.X\s*/\s*操作X\s*[：:]\s*(.+)", row.replace("〔", ""))
            if m:
                ins_title = m.group(1)
                break
        mid = hashlib.md5((family + "|" + title + "|" + str(i)).encode()).hexdigest()[:8]
        modules.append({
            "id": mid,
            "family": family,
            "title": title,
            "level": lvl,
            "start": i,
            "end": end,
            "elements": content,
            "tables": len(tables),
            "tags": sorted(set(tags)),
            "ins_title": ins_title,
            "first_rows": first_rows,
            "slots": slots[:60],
        })
    return modules


def ppe_glossary(path):
    """读取「劳保用品翻译」一节，得到 中文 → 英文 的对照。"""
    _, root, styles = load(path)
    body = list(root.find("w:body", NS))
    hid = heading_style_ids(styles)
    out = {}
    on = False
    for el in body:
        if el.tag != q("p"):
            continue
        t = clean(text_of(el))
        lvl = _heading_level(el, hid)
        if lvl in (1, 2) and "劳保用品翻译" in t:
            on = True
            continue
        if on and lvl in (1, 2) and t:
            break
        if on and t:
            for en, cn in re.findall(r"([A-Za-z0-9][A-Za-z0-9 \-+]*?)\s*/\s*([0-9A-Za-z]*[\u4e00-\u9fff][\u4e00-\u9fff0-9A-Za-z]*)", t):
                out[cn.strip()] = en.strip()
    return out


def op_title_glossary(path):
    """目录区「操作名称/英文」的对照，例如 加料 → Add。"""
    _, root, _ = load(path)
    out = {}
    for p in root.iter(q("p")):
        t = clean(text_of(p))
        for en, cn in re.findall(r"Ins\.X\s*/\s*操作X\s*[：:]\s*([A-Za-z .]+?)\s*/\s*([\u4e00-\u9fff]+)", t):
            out.setdefault(cn, en.strip())
    return out


def module_elements(root, module):
    body = list(root.find("w:body", NS))
    return [body[j] for j in module["elements"]]


def template_body_modules(template_path):
    """模板正文里自带的示例操作（Ins.1 … Ins.20），作为操作库没有的大类（例如收料）的备选。"""
    from . import mor_doc
    z = zipfile.ZipFile(str(template_path))
    root = etree.fromstring(z.read("word/document.xml"))
    out = []
    for b in mor_doc.ins_blocks(root):
        title = b["title"]
        mid = hashlib.md5(("template|" + title + "|" + str(b["n"])).encode()).hexdigest()[:8]
        slots = []
        for el, a, bb in b["parts"]:
            rows = el.findall(q("tr"))[a:bb] if a is not None else [el]
            for r in rows:
                for run in r.iter(q("r")):
                    if is_pink(run) and run_text(run).strip():
                        slots.append(clean(run_text(run)))
        out.append({
            "id": "tpl-" + mid, "family": b["title_cn"] or title, "title": "模板示例 " + title, "level": 0,
            "template_ins": b["n"], "tables": len(b["parts"]), "tags": ["模板示例"],
            "ins_title": title, "first_rows": [], "slots": slots[:60], "elements": [],
        })
    return out


def save_index(modules, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(modules, f, ensure_ascii=False, indent=1)
