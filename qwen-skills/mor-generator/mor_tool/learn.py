"""从「工艺 → 定稿 MOR」配对里学习，写入 knowledge/。

学到的东西：
1. 操作映射：工艺哪一步对应 MOR 哪几个 Ins（例如 烘料 → 装料 + 烘料）
2. 操作块例子：每个 Ins 的整块表格（已经由专家删减好），以后同类操作优先复用
3. 翻译记忆：物料、设备、标题、劳保、安全措施、操作描述的中英对照
4. 物料别名：工艺写法 → 物料库名称和内部控制号
5. 专家批注：原样存进 feedback/，由人或 AI 提炼成规则
"""

import json
import re
from datetime import datetime
from pathlib import Path

import yaml
from lxml import etree

from . import mor_doc, tech
from .ooxml import NS, W_NS, clean, q, rows_of, text_of

CJK = re.compile(r"[\u4e00-\u9fff]")


def cjk_only(s):
    return "".join(CJK.findall(s or ""))


def bigrams(s):
    s = cjk_only(s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def sim(a, b):
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / float(len(A | B))


def containment(a, b):
    """a 的二元组有多少出现在 b 里。用于「工艺句子是否被 MOR 段落包含」。"""
    A, B = bigrams(a), bigrams(b)
    return len(A & B) / float(len(A)) if A else 0.0


def latin_ratio(s):
    s = s or ""
    letters = len(re.findall(r"[A-Za-z]", s))
    han = len(CJK.findall(s))
    return letters / float(letters + han) if (letters + han) else 0.0


def align(ops, blocks, seed=None):
    """动态规划把工艺操作对齐到 MOR 块。每个工艺操作对应 0~3 个连续的块。"""
    seed = seed or {}
    n, m = len(ops), len(blocks)
    texts = [mor_doc.block_text(b) for b in blocks]
    NEG = -1e9
    dp = [[NEG] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        op = ops[i - 1]
        for j in range(0, m + 1):
            for k in range(0, 4):
                if j - k < 0 or dp[i - 1][j - k] <= NEG / 2:
                    continue
                if k == 0:
                    score = -0.3
                else:
                    seg = " ".join(texts[j - k:j])
                    score = containment(op["text"], seg)
                    titles = [blocks[x]["title_en"] for x in range(j - k, j)]
                    expected = [t[0] for t in seed.get(op["name"], [])]
                    if expected and titles == expected:
                        score += 0.5
                    if k > 1:
                        score -= 0.05 * (k - 1)
                v = dp[i - 1][j - k] + score
                if v > dp[i][j]:
                    dp[i][j] = v
                    back[i][j] = k
    out = []
    j = m
    for i in range(n, 0, -1):
        k = back[i][j]
        out.append((i - 1, list(range(j - k, j))))
        j -= k
    out.reverse()
    return out


def _paragraphs(block_els):
    """枚举块里所有段落及其位置：(part_idx, row_idx, cell_idx, para_idx, p)。"""
    for pi, el in enumerate(block_els):
        if el.tag == q("p"):
            yield pi, None, None, None, el
            continue
        for ri, tr in enumerate(rows_of(el)):
            for ci, tc in enumerate(tr.findall(q("tc"))):
                for k, p in enumerate(tc.findall(q("p"))):
                    yield pi, ri, ci, k, p


def find_roles(block_els, op):
    """在一个 MOR 块里找出：安全行段落、操作描述的英文段和中文段。"""
    paras = list(_paragraphs(block_els))
    roles = {"safety": None, "instruction_cn": None, "instruction_en": None}
    best, best_s = None, 0.0
    for pi, ri, ci, k, p in paras:
        t = clean(text_of(p))
        if not CJK.search(t) or latin_ratio(t) > 0.6:
            continue
        s = containment(op["text"], t) if op else 0
        if s > best_s:
            best, best_s = (pi, ri, ci, k), s
    if best and best_s >= 0.35:
        roles["instruction_cn"] = list(best) + [round(best_s, 3)]
        pi, ri, ci, k = best
        if k and k > 0:
            prev = [x for x in paras if x[:3] == (pi, ri, ci) and x[3] == k - 1]
            if prev and latin_ratio(clean(text_of(prev[0][4]))) > 0.6:
                roles["instruction_en"] = [pi, ri, ci, k - 1]
    for pi, ri, ci, k, p in paras:
        if ri is None or ri == 0:
            continue
        t = clean(text_of(p))
        if t.startswith("Wear ") or "劳保" in t:
            roles["safety"] = [pi, ri, ci]
            break
    return roles


def _xml_of(elements):
    wrap = etree.Element("{%s}document" % W_NS, nsmap={"w": W_NS, "r": NS["r"]})
    body = etree.SubElement(wrap, "{%s}body" % W_NS)
    for el in elements:
        body.append(el)
    return etree.tostring(wrap, encoding="utf-8", xml_declaration=True)


def _split_bilingual_line(t):
    """「English text. /中文」或「English/中文」拆开。"""
    first_cjk = CJK.search(t)
    if not first_cjk:
        return None, None
    cut = t.rfind("/", 0, first_cjk.start())
    if cut <= 0:
        return None, None
    en, cn = t[:cut].strip(), t[cut + 1:].strip()
    if latin_ratio(en) > 0.5 and CJK.search(cn):
        return en, cn
    return None, None


def learn_pair(tech_path, mor_path, kn, rules_seed=None, pair_id=None):
    proc = tech.parse(tech_path)
    root, styles, comments = mor_doc.load(mor_path)
    blocks = mor_doc.ins_blocks(root)
    pair_id = pair_id or Path(mor_path).stem
    source = Path(mor_path).name
    summary = {"pair_id": pair_id, "new_terms": 0, "new_aliases": 0, "new_mappings": 0, "examples": 0, "comments": len(comments)}

    seed = {}
    for name, seq in (rules_seed or {}).items():
        if isinstance(seq, list):
            seed[name] = [(x["title_en"], x["title_cn"]) for x in seq]
    alignment = align(proc["operations"], blocks, seed)

    ex_dir = kn.root / "examples" / pair_id
    ex_dir.mkdir(parents=True, exist_ok=True)
    (ex_dir / "styles.xml").write_bytes(etree.tostring(styles, encoding="utf-8", xml_declaration=True))
    index = {"pair_id": pair_id, "tech": Path(tech_path).name, "mor": source, "learned_at": datetime.now().isoformat(timespec="seconds"),
             "tech_no": proc.get("tech_no"), "ins": []}

    skip = [re.compile(p) for p in ["^体系超温报警", "^上限[:：]", "^下限[:：]"]]
    for op_i, bidx in alignment:
        op = proc["operations"][op_i]
        seq = [(blocks[b]["title_en"], blocks[b]["title_cn"]) for b in bidx]
        if seq and kn.add_mapping(op["name"], seq, source):
            summary["new_mappings"] += 1
        for pos, b in enumerate(bidx):
            blk = blocks[b]
            els = mor_doc.block_elements(blk)
            roles = find_roles(els, op)
            fname = "ins_%02d.xml" % blk["n"]
            (ex_dir / fname).write_bytes(_xml_of(els))
            mats = [m for m in proc["materials"] if m["step"] == op["step"]]
            index["ins"].append({
                "ins": blk["n"], "title_en": blk["title_en"], "title_cn": blk["title_cn"], "optional": blk["optional"],
                "position_in_op": pos, "ops_in_group": len(bidx),
                "op_step": op["step"], "op_name": op["name"], "op_text": op["text"], "op_text_lines": op.get("text_lines", []),
                "op_hazard_lines": op.get("hazard_lines", []), "op_ppe": op.get("ppe", ""),
                "materials": [{"cn": m["name"], "qty_kg": m["qty_kg"]} for m in mats],
                "roles": roles, "file": fname,
            })
            summary["examples"] += 1

            if pos == 0 and roles["safety"]:
                pi, ri, ci = roles["safety"]
                tc = rows_of(els[pi])[ri].findall(q("tc"))[ci]
                lines = [clean(text_of(p)) for p in tc.findall(q("p")) if clean(text_of(p))]
                if lines and op.get("ppe") and op["ppe"] not in ("N/A", ""):
                    en, cn = _split_bilingual_line(lines[0])
                    if en and kn.add_term("ppe", op["ppe"], en, source, cn_mor=cn):
                        summary["new_terms"] += 1
                for hz in op.get("hazard_lines", []):
                    if any(r.search(hz) for r in skip) or hz in ("N/A", ""):
                        continue
                    for line in lines[1:] + lines[:1]:
                        en, cn = _split_bilingual_line(line)
                        if en and cn and containment(hz, cn) > 0.8:
                            if kn.add_term("hazard", hz, en, source, cn_mor=cn):
                                summary["new_terms"] += 1
                            break
            if roles["instruction_cn"] and roles["instruction_en"]:
                def para_at(loc):
                    pi, ri, ci, k = loc[:4]
                    el = els[pi]
                    if ri is None:
                        return el
                    return rows_of(el)[ri].findall(q("tc"))[ci].findall(q("p"))[k]
                en = clean(text_of(para_at(roles["instruction_en"])))
                cn_mor = clean(text_of(para_at(roles["instruction_cn"])))
                if kn.add_term("instruction", op["text"], en, source, cn_mor=cn_mor):
                    summary["new_terms"] += 1
            if kn.add_term("title", blk["title_cn"], blk["title_en"], source):
                summary["new_terms"] += 1

    (ex_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    for m in mor_doc.material_rows(root):
        if kn.add_term("material", m["name_cn"], m["name_en"], source):
            summary["new_terms"] += 1
    for e in mor_doc.equipment_rows(root):
        cn = re.sub(r"^L", "", e["cn"]).strip()
        if kn.add_term("equipment", cn, e["en"], source):
            summary["new_terms"] += 1
    for c in mor_doc.control_numbers(root):
        if kn.add_alias(c["cn"], "", c["control_no"], c["en"], source):
            summary["new_aliases"] += 1

    front = {
        "sampling_rows": mor_doc.sampling_rows(root),
        "tech_sampling": proc.get("sampling", []),
        "product_name_en": _cover_name(root),
    }
    (ex_dir / "front.json").write_text(json.dumps(front, ensure_ascii=False, indent=1), encoding="utf-8")

    if comments:
        lines = ["# 专家批注：%s" % source, "", "工艺：%s" % Path(tech_path).name, "",
                 "每条批注提炼成规则后，在 rules/ 或 knowledge/ 里改，并在这里打勾。", ""]
        for c in comments:
            if not c["text"]:
                continue
            lines.append("- [ ] 批注 %s（%s）：%s" % (c["id"], c["author"], c["text"]))
            if c["anchor"]:
                lines.append("  - 原文：%s" % c["anchor"][:160])
        (kn.root / "feedback" / ("%s.md" % pair_id)).write_text("\n".join(lines) + "\n", encoding="utf-8")

    kn.save()
    kn.log("## %s 学习 %s\n- 工艺：%s\n- 新译名/句子 %d，新物料别名 %d，新操作映射 %d，操作块例子 %d，批注 %d" % (
        datetime.now().strftime("%Y-%m-%d %H:%M"), source, Path(tech_path).name,
        summary["new_terms"], summary["new_aliases"], summary["new_mappings"], summary["examples"], summary["comments"]))
    summary["alignment"] = [(proc["operations"][i]["step_raw"], proc["operations"][i]["name"], [blocks[b]["n"] for b in bs]) for i, bs in alignment]
    return summary


def _cover_name(root):
    els = mor_doc.body_elements(root)
    for i, el in enumerate(els):
        if el.tag == q("p") and clean(text_of(el)).startswith("Master Operation Record For"):
            for nxt in els[i + 1:i + 4]:
                t = clean(text_of(nxt))
                if t:
                    return t
    return ""
