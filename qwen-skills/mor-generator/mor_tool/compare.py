"""把生成的 MOR 和人工定稿的 MOR 逐节对比，用来衡量工具质量、找系统性问题。"""

import re
from pathlib import Path

from . import learn, mor_doc
from .ooxml import clean, q, text_of


def _front(root):
    out = {}
    for p in root.iter(q("p")):
        t = clean(text_of(p))
        m = re.search(r"MOR编号和版本号[：:]\s*(\S+)", t)
        if m and "mor_no" not in out:
            out["mor_no"] = m.group(1)
        m = re.search(r"Expected yield\s*/预期收率[：:]\s*([\d~\-\. ]+)%", t)
        if m and "yield" not in out:
            out["yield"] = re.sub(r"\s+", "", m.group(1))
        m = re.search(r"分子量=\(_+kg/\s*([\d.]+)\s*\)\s*×\s*([\d.]+)", t.replace(" ", ""))
        if m and "mw" not in out:
            out["mw"] = (m.group(1), m.group(2))
        if t.startswith("Operation Record for") and "code" not in out:
            out["code"] = t.replace("Operation Record for", "").strip()
    return out


def compare(gen_path, ref_path):
    g, _, _ = mor_doc.load(gen_path)
    r, _, _ = mor_doc.load(ref_path)
    res = {}
    gf, rf = _front(g), _front(r)
    res["front"] = [(k, gf.get(k), rf.get(k), gf.get(k) == rf.get(k)) for k in ("mor_no", "code", "yield", "mw")]

    gb, rb = mor_doc.ins_blocks(g), mor_doc.ins_blocks(r)
    gt = [(b["n"], b["title_en"], b["title_cn"], b["optional"]) for b in gb]
    rt = [(b["n"], b["title_en"], b["title_cn"], b["optional"]) for b in rb]
    res["ins_gen"], res["ins_ref"] = gt, rt
    same_titles = sum(1 for a, b in zip(gt, rt) if a[1] == b[1])
    res["ins_title_match"] = (same_titles, max(len(gt), len(rt)))
    sims = []
    for a, b in zip(gb, rb):
        sims.append((a["n"], round(learn.sim(mor_doc.block_text(a), mor_doc.block_text(b)), 3)))
    res["ins_text_sim"] = sims

    gm = mor_doc.material_rows(g)
    rm = mor_doc.material_rows(r)

    def key(m):
        return (m["ins"].replace("□", "").replace("FORMCHECKBOX", "").strip(), m["name_cn"])
    rk = {key(m): m for m in rm}
    mat = []
    for m in gm:
        ref = rk.get(key(m))
        if ref is None:
            mat.append((key(m), "多出", m["name_en"], ""))
            continue
        diffs = [f for f in ("name_en", "mw", "density", "kg_ratio", "mol_ratio")
                 if f in m and f in ref and (m.get(f) or "").strip() != (ref.get(f) or "").strip()]
        mat.append((key(m), "一致" if not diffs else "不同：" + "、".join("%s %s→%s" % (f, m.get(f), ref.get(f)) for f in diffs), m["name_en"], ref["name_en"]))
    gk = {key(m) for m in gm}
    for m in rm:
        if key(m) not in gk:
            mat.append((key(m), "缺少", "", m["name_en"]))
    res["materials"] = mat

    ge = [e["en"] for e in mor_doc.equipment_rows(g)]
    re_ = [e["en"] for e in mor_doc.equipment_rows(r)]
    res["equipment"] = {"gen": ge, "ref": re_, "common": sorted(set(ge) & set(re_)), "missing": sorted(set(re_) - set(ge)), "extra": sorted(set(ge) - set(re_))}

    gc = {c["cn"]: c["control_no"] for c in mor_doc.control_numbers(g)}
    rc = {c["cn"]: c["control_no"] for c in mor_doc.control_numbers(r)}
    res["control_numbers"] = [(k, gc.get(k), v, gc.get(k) == v) for k, v in rc.items()]

    gs, rs = mor_doc.sampling_rows(g), mor_doc.sampling_rows(r)
    res["sampling"] = {"gen_rows": len(gs), "ref_rows": len(rs),
                       "same_rows": sum(1 for a, b in zip(gs, rs) if [x for x in a if x] == [x for x in b if x])}
    return res


def summary_line(res):
    a, b = res["ins_title_match"]
    sims = [s for _, s in res["ins_text_sim"]]
    avg = sum(sims) / len(sims) if sims else 0
    mats = res["materials"]
    ok = sum(1 for m in mats if m[1] == "一致")
    cn = res["control_numbers"]
    return ("Ins 标题一致 %d/%d，块文字平均相似度 %.2f；原料行一致 %d/%d；内部控制号一致 %d/%d；设备重合 %d/%d；分析方法行一致 %d/%d" % (
        a, b, avg, ok, len(mats), sum(1 for x in cn if x[3]), len(cn), len(res["equipment"]["common"]), len(set(res["equipment"]["ref"])),
        res["sampling"]["same_rows"], res["sampling"]["ref_rows"]))


def to_markdown(res, gen, ref):
    lines = ["# 生成 MOR 与人工 MOR 对比", "", "生成：%s" % Path(gen).name, "", "人工：%s" % Path(ref).name, "",
             "**%s**" % summary_line(res), "", "## 首页和产品信息", "", "| 项 | 生成 | 人工 | 一致 |", "|---|---|---|---|"]
    for k, a, b, same in res["front"]:
        lines.append("| %s | %s | %s | %s |" % (k, a, b, "是" if same else "否"))
    lines += ["", "## 操作序列", "", "| 生成 Ins | 人工 Ins | 标题一致 | 块文字相似度 |", "|---|---|---|---|"]
    sims = dict(res["ins_text_sim"])
    for i in range(max(len(res["ins_gen"]), len(res["ins_ref"]))):
        a = res["ins_gen"][i] if i < len(res["ins_gen"]) else None
        b = res["ins_ref"][i] if i < len(res["ins_ref"]) else None
        lines.append("| %s | %s | %s | %s |" % (
            "%d %s/%s%s" % (a[0], a[1], a[2], "（可选）" if a[3] else "") if a else "",
            "%d %s/%s%s" % (b[0], b[1], b[2], "（可选）" if b[3] else "") if b else "",
            "是" if a and b and a[1] == b[1] else "否", sims.get(a[0], "") if a else ""))
    lines += ["", "## 原料表", "", "| 操作号/物料 | 结果 | 生成英文名 | 人工英文名 |", "|---|---|---|---|"]
    for k, st, a, b in res["materials"]:
        lines.append("| %s %s | %s | %s | %s |" % (k[0], k[1], st, a, b))
    e = res["equipment"]
    lines += ["", "## 设备清单", "", "- 共同：%s" % "、".join(e["common"]), "- 人工有、生成没有：%s" % ("、".join(e["missing"]) or "无"),
              "- 生成有、人工没有：%s" % ("、".join(e["extra"]) or "无"), "", "## 内部控制号", "", "| 物料 | 生成 | 人工 | 一致 |", "|---|---|---|---|"]
    for k, a, b, same in res["control_numbers"]:
        lines.append("| %s | %s | %s | %s |" % (k, a, b, "是" if same else "否"))
    s = res["sampling"]
    lines += ["", "## 分析方法表", "", "生成 %d 行，人工 %d 行，完全一致 %d 行。" % (s["gen_rows"], s["ref_rows"], s["same_rows"]), ""]
    return "\n".join(lines)
