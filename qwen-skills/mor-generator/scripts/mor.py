#!/usr/bin/env python3
"""MOR 生成与复核工具的命令行入口。

  python qwen-skills/mor-generator/scripts/mor.py parse  工艺.docx            -o process.json
  python qwen-skills/mor-generator/scripts/mor.py plan   工艺.docx            -o mor_plan.json
  python qwen-skills/mor-generator/scripts/mor.py fill   mor_plan.json  ai_fills.json
  python qwen-skills/mor-generator/scripts/mor.py build  mor_plan.json        -o MOR草稿.docx
  python qwen-skills/mor-generator/scripts/mor.py run    工艺.docx            -o 输出目录/
  python qwen-skills/mor-generator/scripts/mor.py check  MOR.docx  [--tech 工艺.docx] [--fix]
  python qwen-skills/mor-generator/scripts/mor.py learn  工艺.docx  定稿MOR.docx
  python qwen-skills/mor-generator/scripts/mor.py compare 生成.docx 人工.docx  -o 对比.md

全局参数放在子命令前：--validation yes|no  --template 模板配置名  --knowledge 知识库目录
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mor_tool import builder, checker, compare, learn, plan, tech  # noqa: E402
from mor_tool.session import Session  # noqa: E402


def _validation(a):
    return None if a.validation is None else a.validation == "yes"


def _dump(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_parse(a):
    proc = tech.parse(a.tech)
    _dump(proc, a.output or "process.json")
    print("已解析：%d 个操作，%d 条物料，%d 条取样；警告 %d 条" % (len(proc["operations"]), len(proc["materials"]), len(proc["sampling"]), len(proc["warnings"])))


def _make_plan(a, s):
    proc = tech.parse(a.tech)
    p = plan.build_plan(proc, s.cfg, s.kn, s.modules, s.matlib, s.ppe_glossary, use_examples=not a.no_examples)
    return proc, p


def cmd_plan(a):
    s = Session(a.template, a.knowledge, _validation(a))
    _, p = _make_plan(a, s)
    out = a.output or "mor_plan.json"
    _dump(p, out)
    t = p["todo_summary"]
    print("已生成计划 %s：%d 个 Ins；需要 AI 补的 %d 处，需要人工填的 %d 处" % (out, len(p["ins"]), len(t["needs_ai"]), len(t["todo"])))


def cmd_fill(a):
    p = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    fills = json.loads(Path(a.fills).read_text(encoding="utf-8"))
    plan.apply_fills(p, fills)
    _dump(p, a.output or a.plan)
    t = p["todo_summary"]
    print("已写入 %d 处；还剩 AI 待补 %d 处，人工待填 %d 处" % (len(fills), len(t["needs_ai"]), len(t["todo"])))
    for x in t["needs_ai"]:
        print("  AI 待补：%s" % x)


def _write_report(rep, plan_obj, path):
    lines = ["# MOR 生成报告：%s" % (plan_obj["meta"]["mor_no"] or ""), "",
             "工艺：%s　模板：%s　验证项目：%s" % (plan_obj["meta"]["tech_no"], plan_obj["meta"]["template"], "是" if plan_obj["meta"]["validation"] else "否"),
             "复用的例子：%s" % ("、".join(plan_obj["meta"]["examples_used"]) or "无（只用操作库）"), "",
             "## 每个操作的来源", "", "| Ins | 标题 | 工艺步骤 | 来源 |", "|---|---|---|---|"]
    for e in plan_obj["ins"]:
        src = e["source"]
        if src["type"] == "example":
            s_txt = "例子 %s Ins.%s（相似度 %.2f%s）" % (src["pair_id"], src["ins"], src["score"], "，原文一致" if src.get("same_text") else "")
        else:
            s_txt = "操作库「%s」" % (src.get("title") or "无")
        lines.append("| %d | %s/%s | %s %s | %s |" % (e["n"], e["title_en"], e["title_cn"], e["op_step_raw"], e["op_name"], s_txt))
    todo = [i for i in rep.items if i["level"] == "todo"]
    check = [i for i in rep.items if i["level"] == "check"]
    lines += ["", "## 需要填写（MOR 中黄色高亮）", ""] + ["- %s：%s" % (i["where"], i["what"]) for i in todo]
    lines += ["", "## 建议核对", ""] + ["- %s：%s" % (i["where"], i["what"]) for i in check]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_build(a):
    s = Session(a.template, a.knowledge, _validation(a))
    p = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    rep = builder.build(p, s, a.output)
    rp = Path(a.output).with_suffix(".生成报告.md")
    _write_report(rep, p, rp)
    print("已生成 %s；报告 %s" % (a.output, rp))


def cmd_run(a):
    s = Session(a.template, a.knowledge, _validation(a))
    proc, p = _make_plan(a, s)
    out_dir = Path(a.output or ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (p["meta"]["mor_no"] or "MOR") + "_草稿"
    _dump(proc, out_dir / "process.json")
    _dump(p, out_dir / "mor_plan.json")
    docx = out_dir / (name + ".docx")
    rep = builder.build(p, s, docx)
    _write_report(rep, p, out_dir / (name + ".生成报告.md"))
    res = checker.check(docx, tech_path=a.tech, fix=True, out_path=docx, pages=not a.no_pages)
    (out_dir / (name + ".复核报告.md")).write_text(checker.to_markdown(res), encoding="utf-8")
    t = p["todo_summary"]
    print("已生成 %s\n  Ins %d 个；AI 待补 %d 处；人工待填 %d 处；复核：错误 %d，提示 %d" % (
        docx, len(p["ins"]), len(t["needs_ai"]), len(t["todo"]), len(res["errors"]), len(res["warnings"])))


def cmd_check(a):
    res = checker.check(a.mor, tech_path=a.tech, fix=a.fix, out_path=a.output or a.mor, pages=a.pages)
    md = checker.to_markdown(res)
    out = Path(a.report or Path(a.output or a.mor).with_suffix(".复核报告.md"))
    out.write_text(md, encoding="utf-8")
    print("复核完成：错误 %d，提示 %d，高亮待补 %d；报告 %s" % (len(res["errors"]), len(res["warnings"]), res["highlights"], out))


def cmd_learn(a):
    s = Session(a.template, a.knowledge, _validation(a))
    summary = learn.learn_pair(a.tech, a.mor, s.kn, s.cfg.op_mapping, pair_id=a.id)
    print("已学习 %s：新译名/句子 %d，新物料别名 %d，新操作映射 %d，操作块例子 %d，批注 %d" % (
        summary["pair_id"], summary["new_terms"], summary["new_aliases"], summary["new_mappings"], summary["examples"], summary["comments"]))
    for step, name, ins in summary["alignment"]:
        print("  工艺 %s %s → Ins %s" % (step, name, ins))


def cmd_compare(a):
    res = compare.compare(a.generated, a.reference)
    md = compare.to_markdown(res, a.generated, a.reference)
    Path(a.output or "对比报告.md").write_text(md, encoding="utf-8")
    print(compare.summary_line(res))


def main(argv=None):
    ap = argparse.ArgumentParser(description="MOR 生成与复核工具")
    ap.add_argument("--template", help="rules/templates/ 下的配置名，默认见 config.yaml")
    ap.add_argument("--knowledge", help="知识库目录，默认 qwen-skills/mor-generator/knowledge")
    ap.add_argument("--validation", choices=["yes", "no"], help="是否验证项目（验证批），默认见模板配置 validation")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse"); p.add_argument("tech"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_parse)
    p = sub.add_parser("plan"); p.add_argument("tech"); p.add_argument("-o", "--output")
    p.add_argument("--no-examples", action="store_true", help="不复用学过的例子，只用操作库"); p.set_defaults(func=cmd_plan)
    p = sub.add_parser("fill", help="把 AI 补好的内容按路径写回计划")
    p.add_argument("plan"); p.add_argument("fills"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_fill)
    p = sub.add_parser("build"); p.add_argument("plan"); p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_build)
    p = sub.add_parser("run"); p.add_argument("tech"); p.add_argument("-o", "--output")
    p.add_argument("--no-examples", action="store_true"); p.add_argument("--no-pages", action="store_true", help="不调用 LibreOffice 更新页码引用")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("check"); p.add_argument("mor"); p.add_argument("--tech"); p.add_argument("--fix", action="store_true")
    p.add_argument("--pages", action="store_true", help="用 LibreOffice 排版后更新「Page X of Y」引用")
    p.add_argument("-o", "--output"); p.add_argument("--report"); p.set_defaults(func=cmd_check)
    p = sub.add_parser("learn"); p.add_argument("tech"); p.add_argument("mor"); p.add_argument("--id"); p.set_defaults(func=cmd_learn)
    p = sub.add_parser("compare"); p.add_argument("generated"); p.add_argument("reference"); p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_compare)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
