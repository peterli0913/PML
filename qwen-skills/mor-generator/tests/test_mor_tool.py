"""MOR 工具回归测试。用仓库里的 DH313839301 v.2 / v.3 配对文件。

  python -m unittest discover -s qwen-skills/mor-generator/tests -v

整条流程测试在临时知识库里只学 v.2，再生成 v.3 和人工定稿对比，所以 v.3 始终是留出测试集，
不受 knowledge/ 里已经学过 v.3 的影响。
"""

import copy
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parents[1]
sys.path.insert(0, str(TOOL))

from lxml import etree  # noqa: E402

from mor_tool import builder, checker, compare, learn, plan, tech  # noqa: E402
from mor_tool.ooxml import NS, clean, q, text_of  # noqa: E402
from mor_tool.session import Session  # noqa: E402

DATA = REPO / "MOR相关"
TECH2 = DATA / "Tech-DH313839301_v.2_liyue_07-23-2026.docx"
TECH3 = DATA / "Tech-DH313839301_v.3_liyue_10-21-2026.docx"
MOR2 = DATA / "MOR-DH313839301.02_07-24-2026.docx"
MOR3 = DATA / "MOR-DH313839301.03_10-21-2026.docx"
FILLS3 = TOOL / "tests" / "data" / "ai_fills_v3.json"


VALIDATOR = REPO / ".claude" / "skills" / "docx" / "scripts" / "office" / "validate.py"


def _validate(test, path):
    if not VALIDATOR.exists():
        test.skipTest("没有 docx 校验脚本")
    import subprocess
    r = subprocess.run([sys.executable, str(VALIDATOR), str(path)], capture_output=True, text=True, timeout=600)
    test.assertIn("All validations PASSED", r.stdout + r.stderr, (r.stdout + r.stderr)[-2000:])


def _doc(path):
    with zipfile.ZipFile(str(path)) as z:
        return etree.fromstring(z.read("word/document.xml"))


class TechParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = tech.parse(TECH2)

    def test_identity(self):
        p = self.proc
        self.assertEqual((p["site_code"], p["product_code"], p["step_no"], int(p["tech_version"])), ("DH3", "138393", "01", 2))

    def test_operations_and_materials(self):
        p = self.proc
        self.assertEqual(len(p["operations"]), 20)
        self.assertEqual(p["limiting"]["name"], "L-异亮氨酸")
        names = {m["name"] for m in p["materials"]}
        self.assertTrue({"36%盐酸", "无水乙醇", "碳酸钠", "饮用水"} <= names)
        self.assertTrue(any(o["optional"] for o in p["operations"]))

    def test_route_molecular_weights(self):
        mws = json.dumps(self.proc, ensure_ascii=False)
        self.assertIn("353.42", mws)
        self.assertIn("131.18", mws)


class MaterialLookupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Session(knowledge_dir=tempfile.mkdtemp(prefix="kn-"))

    def test_exact(self):
        self.assertEqual(self.s.matlib.lookup("L-异亮氨酸")["chosen"]["control_no"], "YL001023")

    def test_ambiguous_is_not_guessed(self):
        # 物料库里「盐酸」有两个编号，专家实际用的是「试剂盐酸 YL000451」：没学过时必须标出来让人选
        r = self.s.matlib.lookup("36%盐酸")
        self.assertEqual(r["status"], "ambiguous")
        self.assertGreaterEqual(len({c["control_no"] for c in r["candidates"]}), 2)

    def test_common_sheet_preferred(self):
        self.assertEqual(self.s.matlib.lookup("碳酸钠")["chosen"]["control_no"], "YL000491")

    def test_unknown(self):
        self.assertEqual(self.s.matlib.lookup("不存在的物料XYZ")["status"], "none")


class ColdPlanTest(unittest.TestCase):
    """空知识库：只靠操作库、物料库和规则。"""

    @classmethod
    def setUpClass(cls):
        cls.s = Session(knowledge_dir=tempfile.mkdtemp(prefix="kn-"))
        proc = tech.parse(TECH2)
        cls.plan = plan.build_plan(proc, cls.s.cfg, cls.s.kn, cls.s.modules, cls.s.matlib, cls.s.ppe_glossary)

    def test_mor_number_and_ins_count(self):
        self.assertEqual(self.plan["meta"]["mor_no"], "MOR-DH313839301.02")
        self.assertEqual(len(self.plan["ins"]), 22)

    def test_water_needs_no_control_number(self):
        water = [m for e in self.plan["ins"] for m in e["materials"] if m["cn"] == "饮用水"]
        self.assertTrue(water)
        self.assertTrue(all(m["control_status"] == "ok" for m in water))

    def test_limiting_accuracy(self):
        lim = [m for m in self.plan["materials"] if m["limiting"]]
        self.assertEqual(lim[0]["accuracy"], "±0.5%")

    def test_apply_fills(self):
        p = copy.deepcopy(self.plan)
        path = next(x for x in p["todo_summary"]["needs_ai"] if x.endswith(".instruction"))
        plan.apply_fills(p, [{"path": path, "value": {"cn": "测试", "en": "test"}}])
        self.assertNotIn(path, p["todo_summary"]["needs_ai"])
        with self.assertRaises(ValueError):
            plan.apply_fills(p, [{"path": p["todo_summary"]["needs_ai"][0], "value": "只给字符串"}])

    def test_cold_build_is_schema_valid(self):
        out = Path(tempfile.mkdtemp(prefix="mor-cold-")) / "cold.docx"
        builder.build(copy.deepcopy(self.plan), self.s, out)
        self.assertEqual(checker.check(out, fix=True, out_path=out)["ins_count"], 22)
        _validate(self, out)

    def test_learned_alias_resolves_ambiguous_material(self):
        m = [m for e in self.plan["ins"] for m in e["materials"] if m["cn"] == "36%盐酸"][0]
        self.assertNotEqual(m["control_status"], "ok")
        shipped = Session()
        m2 = plan.material_entry({"name": "36%盐酸", "limiting": False, "qty_kg": "1", "volume_m3": "--", "density": "1.19",
                                  "fw": "--", "kg_per_kg": "--", "mol_ratio": "--", "optional": False, "step": "2", "source": ""},
                                 shipped.kn, shipped.matlib, shipped.cfg, False, None)
        self.assertEqual((m2["control_no"], m2["control_status"]), ("YL000451", "ok"))


class ValidationModeTest(unittest.TestCase):
    """验证项目：标准投料量和可接受称量范围要算出来；例子里空着的投料量不能原样沿用。"""

    @classmethod
    def setUpClass(cls):
        cls.s = Session(validation=True)
        cls.plan = plan.build_plan(tech.parse(TECH3), cls.s.cfg, cls.s.kn, cls.s.modules, cls.s.matlib, cls.s.ppe_glossary)

    def test_standard_quantity_and_range(self):
        lim = [m for m in self.plan["materials"] if m["limiting"]][0]
        self.assertEqual(lim["cn"], "L-异亮氨酸")
        self.assertEqual((lim["standard_qty"], lim["range"]), ("220.0", "218.9~221.1"))

    def test_blank_example_quantities_not_kept(self):
        e = self.plan["ins"][1]
        self.assertEqual(e["instruction"]["status"], "needs_ai")
        self.assertIn("880.0kg", e["instruction"]["cn"])

    def test_build_flags_remaining_blanks(self):
        out = Path(tempfile.mkdtemp(prefix="mor-val-")) / "val.docx"
        rep = builder.build(copy.deepcopy(self.plan), self.s, out)
        self.assertTrue(any("验证项目" in i["what"] for i in rep.items))
        _validate(self, out)


class ReportDocxTest(unittest.TestCase):
    def test_markdown_subset_to_word(self):
        from docx import Document
        from mor_tool.report_docx import write_report
        md = "# 标题\n\n**结果：错误 0**\n\n## 表\n\n| 项 | 值 |\n|---|---|\n| a | 【待补：编号】 |\n\n- 列表一\n- 列表二\n"
        out = write_report(md, Path(tempfile.mkdtemp(prefix="rep-")) / "r")
        self.assertEqual(out.suffix, ".docx")
        d = Document(str(out))
        self.assertEqual(len(d.tables), 1)
        self.assertEqual([c.text for c in d.tables[0].rows[1].cells], ["a", "【待补：编号】"])
        self.assertTrue(any(r.font.highlight_color for c in d.tables[0].rows[1].cells for p in c.paragraphs for r in p.runs))
        self.assertTrue(any(p.style.name == "List Bullet" for p in d.paragraphs))
        self.assertTrue(any(r.bold for p in d.paragraphs for r in p.runs if "结果" in r.text))


class CheckboxRenderCopyTest(unittest.TestCase):
    def test_checkbox_field_becomes_box(self):
        w = NS["w"]
        xml = ('<w:p xmlns:w="%s"><w:r><w:rPr><w:b/></w:rPr><w:fldChar w:fldCharType="begin"><w:ffData><w:checkBox/></w:ffData></w:fldChar></w:r>'
               '<w:r><w:instrText> FORMCHECKBOX </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
               '<w:r><w:t>衬塑离心机</w:t></w:r></w:p>') % w
        p = etree.fromstring(xml)
        self.assertEqual(checker._checkbox_fields_to_text(p), 1)
        self.assertEqual(clean(text_of(p)), "□衬塑离心机")
        self.assertEqual(len(list(p.iter(q("fldChar")))), 0)
        self.assertIsNotNone(p.find(".//w:b", NS))


class PipelineTest(unittest.TestCase):
    """学 v.2 → 生成 v.3 → 复核 → 和人工定稿 v.3 对比。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="mor-test-"))
        kn_dir = cls.tmp / "knowledge"
        s0 = Session(knowledge_dir=kn_dir)
        cls.learned = learn.learn_pair(TECH2, MOR2, s0.kn, s0.cfg.op_mapping, pair_id="DH313839301-v2")
        s = Session(knowledge_dir=kn_dir)
        proc = tech.parse(TECH3)
        cls.plan = plan.build_plan(proc, s.cfg, s.kn, s.modules, s.matlib, s.ppe_glossary)
        cls.needs_ai_before = list(cls.plan["todo_summary"]["needs_ai"])
        plan.apply_fills(cls.plan, json.loads(FILLS3.read_text(encoding="utf-8")))
        cls.out = cls.tmp / "MOR-DH313839301.03_草稿.docx"
        builder.build(cls.plan, s, cls.out)
        cls.check = checker.check(cls.out, tech_path=TECH3, fix=True, out_path=cls.out)
        cls.cmp = compare.compare(cls.out, MOR3)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_learn_summary(self):
        self.assertEqual(self.learned["examples"], 22)
        self.assertGreaterEqual(self.learned["new_aliases"], 5)

    def test_only_few_ai_items_with_example(self):
        self.assertLessEqual(len(self.needs_ai_before), 6)
        self.assertEqual(self.plan["todo_summary"]["needs_ai"], [])

    def test_docx_is_valid_zip_with_body(self):
        with zipfile.ZipFile(str(self.out)) as z:
            self.assertIsNone(z.testzip())
            self.assertIn("updateFields", z.read("word/settings.xml").decode("utf-8"))
        _validate(self, self.out)

    def test_check_has_no_errors(self):
        self.assertEqual(self.check["errors"], [])
        self.assertEqual(self.check["ins_count"], 22)

    def test_matches_expert_mor(self):
        c = self.cmp
        self.assertEqual(c["ins_title_match"], (22, 22))
        sims = [s for _, s in c["ins_text_sim"]]
        self.assertGreaterEqual(sum(sims) / len(sims), 0.8)
        self.assertTrue(all(x[3] for x in c["control_numbers"]))
        self.assertEqual(dict((k, same) for k, _, _, same in c["front"])["mor_no"], True)

    def test_checker_flags_planted_number(self):
        doc = _doc(self.out)
        nums = re.compile(r"(\d+)~(\d+)℃")
        for p in doc.iter(q("p")):
            for t in p.iter(q("t")):
                if t.text and nums.search(t.text) and re.search(r"[\u4e00-\u9fff]", clean(text_of(p))):
                    m = nums.search(t.text)
                    planted = "%d~%s℃" % (int(m.group(1)) + 37, m.group(2))
                    t.text = t.text.replace(m.group(0), planted, 1)
                    break
            else:
                continue
            break
        else:
            self.skipTest("草稿里没有找到温度范围")
        bad = self.tmp / "planted.docx"
        with zipfile.ZipFile(str(self.out)) as zi, zipfile.ZipFile(str(bad), "w", zipfile.ZIP_DEFLATED) as zo:
            for item in zi.infolist():
                data = zi.read(item.filename)
                if item.filename == "word/document.xml":
                    data = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
                zo.writestr(item, data)
        res = checker.check(bad, tech_path=TECH3)
        self.assertTrue(any(planted in w for w in res["warnings"]), res["warnings"])

    def test_renumber_after_deleting_an_ins(self):
        from mor_tool import mor_doc
        doc = _doc(self.out)
        blocks = mor_doc.ins_blocks(doc)
        for el, a, b in blocks[1]["parts"]:
            if a is None:
                el.getparent().remove(el)
            else:
                from mor_tool.ooxml import rows_of
                for tr in rows_of(el)[a:b]:
                    el.remove(tr)
        bad = self.tmp / "gap.docx"
        with zipfile.ZipFile(str(self.out)) as zi, zipfile.ZipFile(str(bad), "w", zipfile.ZIP_DEFLATED) as zo:
            for item in zi.infolist():
                data = zi.read(item.filename)
                if item.filename == "word/document.xml":
                    data = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
                zo.writestr(item, data)
        self.assertTrue(any("不连续" in e for e in checker.check(bad)["errors"]))
        fixed = checker.check(bad, fix=True, out_path=self.tmp / "gap_fixed.docx")
        self.assertTrue(any("Ins" in f for f in fixed["fixed"]), fixed["fixed"])
        self.assertEqual([b["n"] for b in mor_doc.ins_blocks(_doc(self.tmp / "gap_fixed.docx"))], list(range(1, 22)))


if __name__ == "__main__":
    unittest.main()
