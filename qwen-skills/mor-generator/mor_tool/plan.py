"""由 process.json 生成 mor_plan.json：MOR 每一节要填什么、每个 Ins 用哪个块、哪些地方还需要 AI 或人补。

计划是给人看、给 AI 改的中间文件。凡是 status 为 needs_ai 的地方，由 AI 按 SKILL.md 补齐；
status 为 todo 的地方在 MOR 里黄色高亮，由编写人填写。
"""

import math
import re

from . import learn
from .knowledge import norm_key

NEEDS_AI = "needs_ai"
TODO = "todo"
OK = "ok"


def _num(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _dec(s):
    s = str(s or "")
    return len(s.split(".")[1]) if re.match(r"^-?\d+\.\d+$", s) else 0


def _fmt(v, d):
    return ("%." + str(d) + "f") % v


def mor_number(proc, cfg):
    pat = cfg.common["mor_number"]["pattern"]
    if not proc.get("tech_id"):
        return None
    return pat.format(site=proc["site_code"], product=proc["product_code"], step=proc["step_no"], version=proc["tech_version"])


def _op_titles(op, kn, cfg):
    learned = kn.mapping_for(op["name"]) if kn else None
    if learned:
        return learned, "learned"
    seed = cfg.op_mapping.get(op["name"])
    if isinstance(seed, list):
        return [(x["title_en"], x["title_cn"]) for x in seed], "rules"
    return [("【待补】", op["name"])], "unknown"


def _seed_family(op, pos, cfg):
    seed = cfg.op_mapping.get(op["name"])
    if isinstance(seed, list) and pos < len(seed):
        return seed[pos].get("family", ""), seed[pos].get("prefer", "")
    return op["name"], ""


def _conditions(op, cfg):
    words = cfg.op_mapping.get("condition_words", {}) or {}
    tags = set()
    for tag, pats in words.items():
        for p in pats or []:
            if re.search(p, op["text"]):
                tags.add(tag)
    return tags


def choose_example(entry, op, examples, min_score=0.3):
    best, best_s = None, 0.0
    for ex in examples:
        if ex["title_en"] != entry["title_en"]:
            continue
        s = learn.sim(op["text"], ex["op_text"])
        if ex["op_name"] == op["name"]:
            s += 0.1
        if ex.get("position_in_op") == entry["position_in_op"] and ex.get("ops_in_group") == entry["ops_in_group"]:
            s += 0.05
        if s > best_s:
            best, best_s = ex, s
    if best and best_s >= min_score:
        return best, round(best_s, 3)
    return None, round(best_s, 3)


def choose_module(entry, op, modules, cfg, mat_states):
    family, prefer = _seed_family(op, entry["position_in_op"], cfg)
    prefer_tags = set(cfg.template.get("library_tags_prefer", []))
    avoid_tags = set(cfg.template.get("library_tags_avoid", []))
    conds = _conditions(op, cfg)
    want = set(conds)
    if entry["title_en"] == "Add":
        if any(s == "水" for s in mat_states):
            want.add("水")
        elif any(s == "固体" for s in mat_states):
            want.add("固体")
        elif any(s == "液体" for s in mat_states):
            want.add("液体")
    scored = []
    for m in modules:
        fam_hit = bool(family) and m["family"].startswith(family)
        title_hit = bool(entry["title_cn"]) and m["ins_title"].replace(" ", "").startswith(
            (entry["title_en"] + "/" + entry["title_cn"]).replace(" ", ""))
        if not (fam_hit or title_hit):
            continue
        s = 1.0 if fam_hit else 0.6
        if "模板示例" in m["tags"]:
            s -= 0.3
        if prefer and prefer in m["title"]:
            s += 1.0
        tags = set(m["tags"])
        s += 0.4 * len(tags & prefer_tags)
        s -= 0.6 * len(tags & avoid_tags)
        s += 0.5 * len(tags & want)
        s -= 0.2 * len((tags - want - prefer_tags) & {"控温", "分批", "固体", "液体", "水", "无机盐", "折算", "KF", "体积选择", "补加", "分锅", "淋洗", "不淋洗"})
        if "淋洗" in want and "不淋洗" in tags:
            s -= 0.8
        if "淋洗" not in want and "不淋洗" in tags:
            s += 0.4
        if "补加" not in want and "不补加" in tags:
            s += 0.4
        if "多次" in want and "单次" in tags:
            s -= 0.5
        scored.append((round(s, 2), m))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return None, [], sorted(want)
    return scored[0][1], [(s, m["id"], m["title"]) for s, m in scored[:5]], sorted(want)


WATER_NAMES = {"水", "饮用水", "纯化水", "纯水", "去离子水", "注射用水", "自来水", "工艺用水"}


def is_water(name):
    n = (name or "").strip()
    return n in WATER_NAMES or (n.endswith("水") and not n.startswith("无水") and len(n) <= 5 and "盐" not in n)


def _rows_needed(qty, state, cfg):
    rule = cfg.common["charging_rows"]
    q = _num(qty)
    if q is None:
        return rule.get("min_rows", 2)
    cap = rule["solid_kg_per_container"] if state == "固体" else rule["liquid_kg_per_container"]
    return max(rule.get("min_rows", 2), int(math.ceil(q / float(cap))) + 1)


def _state_guess(m, matlib):
    st = matlib.state_of(m["name"]) if matlib else ""
    if st:
        return st, "物料库"
    if "水" in m["name"] and m.get("density") not in ("--", ""):
        return "液体", "推断"
    if m.get("density") not in ("--", "", None) or m.get("volume_m3") not in ("--", "", None):
        return "液体", "推断：有密度或体积"
    return "固体", "推断：无密度"


def material_entry(m, kn, matlib, cfg, validation, limiting_qty):
    res = matlib.lookup(m["name"]) if matlib else {"status": "none", "chosen": None, "candidates": []}
    alias = None
    for a in (kn.aliases if kn else []):
        if norm_key(a["工艺写法"]) == norm_key(m["name"]):
            alias = a
    control, control_status, note = "", TODO, ""
    if alias and alias.get("内部控制号"):
        control, control_status, note = alias["内部控制号"], OK, "学习自 " + alias["来源"]
    elif res["status"] in ("exact", "alias"):
        control, control_status = res["chosen"]["control_no"], OK
    elif res["status"] in ("partial", "fuzzy"):
        control, control_status = res["chosen"]["control_no"], TODO
        note = "物料库近似匹配「%s」，请确认" % res["chosen"].get("matched_name", res["chosen"]["cn"])
    elif res["status"] == "ambiguous":
        control, control_status = res["chosen"]["control_no"], TODO
        note = "物料库有多个编号：" + "、".join(sorted({c["control_no"] for c in res["candidates"]}))
    elif is_water(m["name"]):
        control_status, note = OK, "工艺用水，MOR 不填内部控制号"
    else:
        note = "物料库查不到，请自填"
    term = kn.term("material", m["name"]) if kn else None
    en, en_status = "", NEEDS_AI
    if term:
        en, en_status = term["en"], OK
    elif alias and alias.get("英文名"):
        en, en_status = alias["英文名"], OK
    elif res.get("chosen") and res["chosen"].get("en") and res["status"] in ("exact", "alias", "partial"):
        en, en_status = res["chosen"]["en"], OK
    state, state_src = _state_guess(m, matlib)
    acc = cfg.common["weighing_accuracy"]["limiting" if m["limiting"] else "non_limiting"]
    entry = {
        "cn": m["name"], "en": en, "en_status": en_status,
        "control_no": control, "control_status": control_status, "control_note": note,
        "qty_kg": m["qty_kg"], "volume_m3": m["volume_m3"], "density": m["density"], "fw": m["fw"],
        "kg_per_kg": m["kg_per_kg"], "mol_ratio": m["mol_ratio"], "limiting": m["limiting"], "optional": m["optional"],
        "state": state, "state_source": state_src, "rows": _rows_needed(m["qty_kg"], state, cfg),
        "accuracy": acc, "step": m["step"], "source": m["source"],
    }
    if validation:
        entry.update(_standard_qty(m, acc, limiting_qty))
    return entry


def _standard_qty(m, acc, limiting_qty):
    pct = _num(acc.replace("±", "").replace("%", "")) / 100.0
    d = _dec(m["qty_kg"])
    if m["limiting"]:
        std = _num(m["qty_kg"])
    else:
        ratio = _num(m["kg_per_kg"])
        std = limiting_qty * ratio if (ratio is not None and limiting_qty is not None) else _num(m["qty_kg"])
    if std is None:
        return {"standard_qty": "", "range": ""}
    lo, hi = std * (1 - pct), std * (1 + pct)
    return {"standard_qty": _fmt(std, d), "range": "%s~%s" % (_fmt(lo, d), _fmt(hi, d))}


def cn_instruction(op, mats, validation, cfg):
    """工艺中文操作描述 → MOR 中文写法：非验证项目挖空数量并加可接受称量范围。"""
    lines = [l for l in (op.get("text_lines") or [op["text"]]) if not re.match(r"^(备注|注)[：:]", l)]
    notes = [l for l in (op.get("text_lines") or []) if re.match(r"^(备注|注)[：:]", l)]
    text = "".join(lines)
    blank = "      "
    if not validation:
        text = re.sub(r"\d+(?:\.\d+)?\s*L(?=搪玻璃|搪瓷|白钢|不锈钢|钛钢|哈氏|双锥|反应釜|釜)", blank + "L", text)
    for m in mats:
        name = re.escape(m["cn"])
        acc = _num(m["accuracy"].replace("±", "").replace("%", "")) / 100.0

        def rng(qs, vs):
            if validation and qs:
                qv, d = _num(qs), _dec(qs)
                part = "%s kg~%s kg" % (_fmt(qv * (1 - acc), d), _fmt(qv * (1 + acc), d))
                if vs:
                    vv, dv = _num(vs), _dec(vs)
                    part += "（%s m3~%s m3）" % (_fmt(vv * (1 - acc), dv), _fmt(vv * (1 + acc), dv))
                return "(Acceptable weighing range/可接受称量范围: %s)" % part
            part = "%skg~%skg" % (blank, blank)
            if vs:
                part += "（%sm3~%sm3）" % (blank, blank)
            return "(Acceptable weighing range/可接受称量范围:%s)" % part

        def repl_before(mo):
            qs, vs, sep = mo.group(1), mo.group(2), mo.group(3)
            qty = (qs + "kg") if validation else (blank + "kg")
            vol = ("（%sm3）" % (vs if validation else blank)) if vs else ""
            return "%s%s%s%s%s" % (qty, vol, sep, mo.group(4), rng(qs, vs))

        text = re.sub(r"(\d+(?:\.\d+)?)\s*[kK][gG](?:\s*（\s*(\d+(?:\.\d+)?)\s*m3\s*）)?(\s*)(%s(?:固体|溶液)?)" % name, repl_before, text)

        def repl_after(mo):
            qs = mo.group(2)
            qty = (qs + "kg") if validation else (blank + "kg")
            return "%s%s%s" % (mo.group(1), qty, rng(qs, None))

        text = re.sub(r"(%s(?:固体|溶液)?)\s*(\d+(?:\.\d+)?)\s*[kK][gG](?!\s*[/／]h)(?!\(Acceptable)" % name, repl_after, text)
    return text, notes


def _safety(op, kn, ppe_gloss, cfg):
    skip_vals = set(cfg.common["safety"]["skip_values"])
    pats = [re.compile(p) for p in cfg.common["safety"]["skip_line_patterns"]]
    lines = []
    ppe = (op.get("ppe") or "").strip()
    if ppe and ppe not in skip_vals:
        term = kn.term("ppe", ppe) if kn else None
        if term:
            lines.append({"kind": "ppe", "cn_src": ppe, "en": term["en"], "cn": term["cn_mor"] or ("戴" + ppe.replace("+", "、")), "status": OK})
        else:
            parts = [x.strip() for x in re.split(r"[+＋、,，]", ppe) if x.strip()]
            ens = [ppe_gloss.get(p) or ppe_gloss.get(p.replace("戴", "")) for p in parts]
            if all(ens):
                en = "Wear " + ", ".join(e[0].lower() + e[1:] if e[:2] != "3M" and e[:4] != "PVCC" else e for e in ens) + "."
                lines.append({"kind": "ppe", "cn_src": ppe, "en": en, "cn": "戴" + "、".join(parts), "status": OK, "note": "按劳保对照表拼接"})
            else:
                lines.append({"kind": "ppe", "cn_src": ppe, "en": "", "cn": "戴" + "、".join(parts), "status": NEEDS_AI,
                              "missing": [p for p, e in zip(parts, ens) if not e]})
    for hz in op.get("hazard_lines") or []:
        hz = hz.strip()
        if not hz or hz in skip_vals or any(p.search(hz) for p in pats):
            continue
        term = kn.term("hazard", hz) if kn else None
        if term:
            lines.append({"kind": "hazard", "cn_src": hz, "en": term["en"], "cn": term["cn_mor"] or hz, "status": OK})
        else:
            lines.append({"kind": "hazard", "cn_src": hz, "en": "", "cn": hz, "status": NEEDS_AI})
    return lines


def _equipment_mentions(text, cfg):
    found = []
    for item in cfg.equipment:
        for mo in re.finditer(item["pattern"], text):
            n = next((g for g in mo.groups() if g), "") if mo.groups() else ""
            key = (item["en"].replace("{n}", "" if item.get("merge") else n))
            if key not in [f["key"] for f in found]:
                found.append({"key": key, "en": item["en"].replace("{n}", "" if item.get("merge") else n),
                              "cn": item["cn"].replace("{n}", "" if item.get("merge") else n),
                              "function": item["function"], "meters": item.get("meters", [])})
    # 「搪玻璃釜1或搪玻璃釜2」「搪玻璃釜1和搪玻璃釜2」都算
    return found


def _example_instruction(src, ex):
    """把例子块里原来的中英文操作描述带进计划，AI 只需要按工艺差异改动。"""
    from pathlib import Path

    from lxml import etree

    from .ooxml import NS, clean, q, rows_of, text_of
    try:
        root = etree.fromstring((Path(src["dir"]) / src["file"]).read_bytes())
    except OSError:
        return {}
    els = list(root.find("w:body", NS))

    def para(loc):
        if not loc:
            return ""
        pi, ri, ci, k = loc[:4]
        try:
            if ri is None:
                return clean(text_of(els[pi]))
            return clean(text_of(rows_of(els[pi])[ri].findall(q("tc"))[ci].findall(q("p"))[k]))
        except (IndexError, TypeError):
            return ""
    roles = src.get("roles") or {}
    return {"example_cn": para(roles.get("instruction_cn")), "example_en": para(roles.get("instruction_en")),
            "example_op_text": ex.get("op_text", "") if ex else "",
            "hint": "对照 example_op_text 和 cn_src 的差异，只改动变化的部分；cn 可以在 example_cn 基础上改"}


def apply_fills(plan, fills):
    """fills: [{"path": "ins[20].instruction.en", "value": "..."}]，或整条写入
    {"path": "ins[20].instruction", "value": {"cn": "...", "en": "..."}}。写入后对应条目状态改为 ok。"""
    for f in fills:
        parts = re.findall(r"[^.\[\]]+|\[\d+\]", f["path"])
        obj = plan
        for p in parts[:-1]:
            obj = obj[int(p[1:-1])] if p.startswith("[") else obj[p]
        last = parts[-1]
        key = int(last[1:-1]) if last.startswith("[") else last
        cur = obj[key] if (isinstance(obj, list) or key in obj) else None
        if isinstance(cur, dict) and "status" in cur:
            if not isinstance(f["value"], dict):
                raise ValueError("%s 是一个条目，请写到具体字段（如 %s.cn / %s.en），或给出 {字段: 值}" % (f["path"], f["path"], f["path"]))
            cur.update(f["value"])
            cur["status"] = OK
            continue
        obj[key] = f["value"]
        if isinstance(obj, dict):
            if "status" in obj and last in ("en", "cn", "value", "rows", "added_en", "criterion", "test"):
                obj["status"] = OK
            if last == "en" and "en_status" in obj:
                obj["en_status"] = OK
            if last == "control_no":
                obj["control_status"] = OK
    plan["todo_summary"] = summarize(plan)
    return plan


def _learned_equipment_name(item, kn):
    """学过的 MOR 里同一设备怎么写，就怎么写（例如 搪玻璃搅拌罐 → Mixing tank/搅拌罐）。"""
    if not kn:
        return {}
    cn = item["cn"].lstrip("L")
    best = None
    for r in kn.glossary:
        if r["kind"] != "equipment":
            continue
        if r["cn"] == cn:
            return {"en": r["en"], "cn": item["cn"], "name_source": "学习"}
        if r["cn"] in cn and not re.search(r"\d$", r["cn"]) and (best is None or len(r["cn"]) > len(best["cn"])):
            best = r
    if best:
        return {"en": best["en"], "cn": best["cn"], "name_source": "学习"}
    return {}


def _sample_source(title_en):
    return {
        "React": "Reaction mixture/反应体系", "Adjust pH": "Reaction mixture/反应体系", "Add": "Reaction mixture/反应体系",
        "Filter": "Filter cake/滤饼", "Dry": "Solid/烘料固体", "Collect": "Product/产品", "Concentrate": "Reaction mixture/反应体系",
        "Extract": "Organic phase/有机相", "Wash": "Organic phase/有机相", "Separate": "Organic phase/有机相",
    }.get(title_en, "")


def build_plan(proc, cfg, kn, modules, matlib, ppe_gloss, use_examples=True):
    validation = cfg.validation
    examples = kn.load_examples() if (kn and use_examples) else []
    lim = proc.get("limiting")
    limiting_qty = _num(lim["qty_kg"]) if lim else None
    plan = {
        "meta": {
            "tech_no": proc.get("tech_no"), "tech_file": proc.get("source"), "mor_no": mor_number(proc, cfg),
            "site_code": proc.get("site_code"), "product_code": proc.get("product_code"), "step_no": proc.get("step_no"),
            "step_of": proc.get("step_of"), "tech_version": proc.get("tech_version"), "template": cfg.template_name,
            "validation": validation, "examples_used": sorted({e["pair_id"] for e in examples}),
        },
        "front": {}, "ins": [], "equipment": [], "materials": [], "sampling": [], "warnings": list(proc.get("warnings", [])),
    }
    site = (cfg.sites or {}).get(proc.get("site_code") or "", {}) or {}
    product_name = ""
    for ex in examples:
        pass
    plan["front"] = {
        "site_address": {"value": site.get("address", ""), "status": OK if site.get("address") else TODO},
        "product_name_en": {"value": product_name, "status": TODO, "note": "产品名称需自填（批注 5）"},
        "product_code": {"value": proc.get("product_code", ""), "status": OK if proc.get("product_code") else TODO},
        "client_code": {"value": "N/A", "status": TODO, "note": "有客户代码时填写"},
        "expected_yield": {"value": proc.get("expected_yield", ""), "status": OK if proc.get("expected_yield") else TODO,
                           "source": "放大生产工艺描述·整体投料计划"},
        "sm_mw": {"value": lim["fw"] if lim else "", "status": OK if lim and lim["fw"] not in ("--", "") else TODO,
                  "source": lim["source"] if lim else ""},
        "product_mw": {"value": proc.get("product_mw", ""), "status": OK if proc.get("product_mw") else TODO,
                       "source": proc.get("product_mw_source", "")},
        "spec": {"value": proc.get("spec_no", ""), "status": OK if proc.get("spec_no") else TODO},
        "batch_size": {"value": (proc.get("overall_plan", {}).get("产量（Kg）", "") if validation else cfg.template.get("footer_batch_size_when_not_validation", "N/A")),
                       "status": OK},
        "changes": [{"steps": c["steps"], "cn": "%s：%s → %s（%s）" % (c["steps"], c["before"], c["after"], c["reason"]), "en": "", "status": NEEDS_AI} for c in proc.get("changes", [])],
    }
    for ex_dir in (kn.example_dirs() if (kn and use_examples) else []):
        front = ex_dir / "front.json"
        idx = ex_dir / "index.json"
        if front.exists() and idx.exists():
            import json
            fj = json.loads(front.read_text(encoding="utf-8"))
            ij = json.loads(idx.read_text(encoding="utf-8"))
            if ij.get("tech_no") and proc.get("tech_id") and ij["tech_no"].startswith(proc["tech_id"]) and fj.get("product_name_en"):
                plan["front"]["product_name_en"] = {"value": fj["product_name_en"], "status": OK, "note": "取自同项目上一版 MOR：" + ij["mor"]}

    n = 0
    ins_of_step = {}
    for op in proc["operations"]:
        titles, title_src = _op_titles(op, kn, cfg)
        op_mats = [m for m in proc["materials"] if m["step"] == op["step"]]
        mats = [material_entry(m, kn, matlib, cfg, validation, limiting_qty) for m in op_mats]
        for pos, (ten, tcn) in enumerate(titles):
            n += 1
            entry = {
                "n": n, "title_en": ten, "title_cn": tcn, "title_source": title_src,
                "optional": bool(op["optional"] or op.get("text_has_checkbox")),
                "op_step": op["step"], "op_step_raw": op["step_raw"], "op_name": op["name"], "op_source": op["source"],
                "position_in_op": pos, "ops_in_group": len(titles),
                "materials": mats if pos == 0 else [],
            }
            ex, ex_score = choose_example(entry, op, examples) if examples else (None, 0.0)
            if ex:
                entry["source"] = {"type": "example", "pair_id": ex["pair_id"], "ins": ex["ins"], "file": ex["file"], "dir": ex["dir"],
                                   "score": ex_score, "same_text": norm_key(ex["op_text"]) == norm_key(op["text"]), "roles": ex["roles"],
                                   "example_materials": ex.get("materials", [])}
            else:
                st = ["水" if is_water(m["cn"]) else m["state"] for m in entry["materials"]]
                mod, cands, want = choose_module(entry, op, modules, cfg, st)
                entry["source"] = {"type": "library", "module": mod["id"] if mod else None, "title": mod["title"] if mod else None,
                                   "candidates": cands, "conditions": want, "example_best_score": ex_score}
            src = entry["source"]
            same_safety = (src["type"] == "example" and ex is not None
                           and [x.strip() for x in ex.get("op_hazard_lines", [])] == [x.strip() for x in op.get("hazard_lines", [])]
                           and (ex.get("op_ppe") or "").strip() == (op.get("ppe") or "").strip())
            entry["safety_keep"] = bool(same_safety)
            entry["safety"] = _safety(op, kn, ppe_gloss, cfg) if (pos == 0 and not same_safety) else []
            term = kn.term("instruction", op["text"]) if kn else None
            cn, notes = cn_instruction(op, entry["materials"] or mats, validation, cfg)
            if src["type"] == "example" and src["same_text"]:
                entry["instruction"] = {"en": "", "cn": "", "status": "keep", "source": "例子块与工艺原文一致，保留"}
            elif src["type"] == "example" and not (src.get("roles") or {}).get("instruction_cn"):
                entry["instruction"] = {"en": "", "cn": "", "status": "keep",
                                        "source": "例子块里这个 Ins 没有操作描述段落（同一工艺操作拆出的其他 Ins 承载描述）"}
            elif term and pos == entry["ops_in_group"] - 1:
                entry["instruction"] = {"en": term["en"], "cn": term["cn_mor"] or cn, "status": OK, "source": "翻译记忆"}
            else:
                entry["instruction"] = {"en": "", "cn": cn, "cn_src": op["text"], "status": NEEDS_AI, "notes_cn": notes}
                if src["type"] == "example":
                    entry["instruction"].update(_example_instruction(src, ex))
            entry["equipment"] = _equipment_mentions(op["text"], cfg)
            plan["ins"].append(entry)
            ins_of_step.setdefault(op["step"], []).append(n)

    eq = {}
    for e in plan["ins"]:
        for item in e["equipment"]:
            item.update(_learned_equipment_name(item, kn))
            rec = eq.setdefault(item["key"], dict(item, ins=[]))
            if e["n"] not in rec["ins"]:
                rec["ins"].append(e["n"])
    plan["equipment"] = sorted(eq.values(), key=lambda x: (min(x["ins"]), x["key"]))

    mats_all = []
    for e in plan["ins"]:
        for m in e["materials"]:
            mats_all.append(dict(m, ins=e["n"], ins_optional=e["optional"]))
    plan["materials"] = mats_all

    for s in proc.get("sampling", []):
        ins_nums = []
        for st in s["steps"]:
            if st in ins_of_step:
                ins_nums.append(ins_of_step[st][-1])
        last = plan["ins"][ins_nums[-1] - 1] if ins_nums else None
        reuse = None
        plan["sampling"].append({
            "steps_raw": s["steps_raw"], "ins": ins_nums, "optional_ins": [ins_of_step[x][-1] for x in s["optional_steps"] if x in ins_of_step],
            "tests_cn": s["tests"], "source_desc": _sample_source(last["title_en"]) if last else "",
            "release": bool(last and last["title_en"] == "Collect"), "rows": reuse, "status": NEEDS_AI, "source": s["source"],
        })
    _reuse_sampling(plan, proc, kn, use_examples)

    plan["todo_summary"] = summarize(plan)
    return plan


def _test_tokens(s):
    return [t for t in re.split(r"[，,、；;\s]+", s or "") if t]


def _reuse_sampling(plan, proc, kn, use_examples):
    """同项目上一版的分析方法表：按「工艺步骤 → 操作号」对应，沿用人工写好的行。

    检测项没变：整组沿用，只换成新的操作号。
    工艺新增了检测项：沿用旧行，另加一行新检测项交给 AI 或人工补。
    """
    if not (kn and use_examples):
        return
    import json
    new_ins_of_step = {}
    for e in plan["ins"]:
        new_ins_of_step.setdefault(e["op_step"], []).append(e["n"])
    optional_new = {e["n"] for e in plan["ins"] if e["optional"]}
    for d in kn.example_dirs():
        f, idx = d / "front.json", d / "index.json"
        if not (f.exists() and idx.exists()):
            continue
        fj = json.loads(f.read_text(encoding="utf-8"))
        ij = json.loads(idx.read_text(encoding="utf-8"))
        step_of_old_ins = {x["ins"]: x["op_step"] for x in ij["ins"]}
        groups, cur = [], None
        for r in fj.get("sampling_rows", []):
            if r and r[0]:
                olds = [int(x) for x in re.findall(r"\d+", r[0])]
                cur = {"old_ins": olds, "rows": [r]}
                groups.append(cur)
            elif cur is not None:
                cur["rows"].append(r)
        for s in plan["sampling"]:
            if s.get("rows"):
                continue
            old = next((o for o in fj.get("tech_sampling", []) if set(o["steps"]) == set(re.findall(r"\d+", s["steps_raw"]))), None)
            if not old:
                continue
            steps = set(old["steps"])
            mine = [g for g in groups if g["old_ins"] and all(step_of_old_ins.get(n) in steps for n in g["old_ins"])]
            if not mine:
                continue
            out_groups = []
            for g in mine:
                new = []
                for n in g["old_ins"]:
                    st = step_of_old_ins.get(n)
                    if st in new_ins_of_step:
                        new.append(new_ins_of_step[st][-1])
                label = ",".join(("□" if n in optional_new else "") + str(n) for n in new)
                rows = [list(r) for r in g["rows"]]
                rows[0][0] = label
                out_groups.append(rows)
            added = [t for t in _test_tokens(s["tests_cn"]) if t not in _test_tokens(old["tests"])]
            s["rows"] = [r for g in out_groups for r in g]
            s["added_tests"] = added
            s["status"] = NEEDS_AI if added else OK
            s["note"] = "沿用 %s 的分析方法行" % d.name + ("；新增检测项：%s" % "、".join(added) if added else "")


def summarize(plan):
    out = {"needs_ai": [], "todo": []}
    for k, v in plan["front"].items():
        if isinstance(v, dict) and v.get("status") in (TODO, NEEDS_AI):
            out[v["status"]].append("front." + k)
    for i, c in enumerate(plan["front"].get("changes", [])):
        if c["status"] == NEEDS_AI:
            out["needs_ai"].append("front.changes[%d]" % i)
    for e in plan["ins"]:
        if e["instruction"]["status"] == NEEDS_AI:
            out["needs_ai"].append("ins[%d].instruction" % (e["n"] - 1))
        for j, s in enumerate(e["safety"]):
            if s["status"] == NEEDS_AI:
                out["needs_ai"].append("ins[%d].safety[%d]" % (e["n"] - 1, j))
        for j, m in enumerate(e["materials"]):
            if m["en_status"] == NEEDS_AI:
                out["needs_ai"].append("ins[%d].materials[%d].en" % (e["n"] - 1, j))
            if m["control_status"] == TODO:
                out["todo"].append("ins[%d].materials[%d].control_no（%s）" % (e["n"] - 1, j, m["control_note"]))
        if e["source"]["type"] == "library" and not e["source"].get("module"):
            out["todo"].append("ins[%d].source（没有合适的模块）" % (e["n"] - 1))
    for i, s in enumerate(plan["sampling"]):
        if s["status"] == NEEDS_AI:
            out["needs_ai"].append("sampling[%d]%s" % (i, ".added_en（新增检测项：%s）" % "、".join(s["added_tests"]) if s.get("added_tests") else ""))
    return out
