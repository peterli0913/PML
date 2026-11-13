"""物料库：按中文名称查内部控制号、英文名和状态（液体/固体/气体）。"""

import csv
import difflib
import re
from pathlib import Path

import xlrd


def _norm(s):
    s = (s or "").strip()
    s = s.replace("（", "(").replace("）", ")").replace(" ", "").replace("\u3000", "")
    return s.lower()


class MaterialLibrary:
    def __init__(self, xls_path, aliases_csv=None):
        self.rows = []
        wb = xlrd.open_workbook(str(xls_path))
        sheet = wb.sheet_by_name("全部常用物料")
        head = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
        idx = {h: i for i, h in enumerate(head)}
        for r in range(1, sheet.nrows):
            get = lambda k: str(sheet.cell_value(r, idx[k])).strip() if k in idx else ""
            self.rows.append({
                "cn": get("中文名称"), "en": get("英文名称"), "control_no": get("内部控制号"),
                "state": get("状态"), "cas": get("CAS"), "sheet": "全部常用物料",
            })
        if "化学品" in wb.sheet_names():
            ch = wb.sheet_by_name("化学品")
            head = [str(ch.cell_value(0, c)).strip() for c in range(ch.ncols)]
            idx = {h: i for i, h in enumerate(head)}
            known = {row["control_no"] for row in self.rows}
            for r in range(1, ch.nrows):
                get = lambda k: str(ch.cell_value(r, idx[k])).strip() if k in idx else ""
                if get("内部控制号") in known:
                    continue
                self.rows.append({
                    "cn": get("中文名称"), "en": get("英文名称"), "control_no": get("内部控制号"),
                    "state": get("状态"), "cas": get("CAS"), "sheet": "化学品",
                })
        self.inorganic = set()
        if "无机盐" in wb.sheet_names():
            s = wb.sheet_by_name("无机盐")
            for r in range(s.nrows):
                for c in range(s.ncols):
                    v = str(s.cell_value(r, c)).strip()
                    if v and v != "无机盐":
                        self.inorganic.add(v)
        self.aliases = {}
        self.alias_rows = {}
        if aliases_csv and Path(aliases_csv).exists():
            with open(aliases_csv, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("工艺写法") and (row.get("物料库名称") or row.get("内部控制号")):
                        self.aliases[_norm(row["工艺写法"])] = (row.get("物料库名称") or "").strip()
                        self.alias_rows[_norm(row["工艺写法"])] = row
        self.by_code = {}
        for row in self.rows:
            self.by_code.setdefault(row["control_no"], row)
        self.common, self.chem = {}, {}
        for row in self.rows:
            target = self.common if row["sheet"] == "全部常用物料" else self.chem
            target.setdefault(_norm(row["cn"]), []).append(row)

    def lookup(self, name):
        """返回 {status, candidates, chosen}。status: exact / alias / partial / ambiguous / none。

        查找顺序：别名表 → 常用物料精确 → 常用物料加「无水」或去掉浓度前缀 → 化学品表精确。
        """
        key = _norm(name)
        stripped = re.sub(r"^\d+(\.\d+)?%", "", key)
        alias = self.alias_rows.get(key)
        if alias and alias.get("内部控制号"):
            row = dict(self.by_code.get(alias["内部控制号"], {}))
            row.setdefault("control_no", alias["内部控制号"])
            row.setdefault("cn", alias.get("物料库名称", ""))
            if alias.get("英文名"):
                row["en_mor"] = alias["英文名"]
            return {"status": "alias", "candidates": [row], "chosen": row, "name": name}
        attempts = []
        if key in self.aliases:
            attempts.append(("alias", self.common, _norm(self.aliases[key])))
            attempts.append(("alias", self.chem, _norm(self.aliases[key])))
        attempts += [
            ("exact", self.common, key),
            ("partial", self.common, _norm("无水" + key)),
            ("partial", self.common, stripped),
            ("partial", self.common, _norm("无水" + stripped)),
            ("exact", self.chem, key),
            ("partial", self.chem, stripped),
        ]
        for status, table, k in attempts:
            hits = table.get(k)
            if not hits:
                continue
            codes = sorted({h["control_no"] for h in hits if h["control_no"]})
            chosen = dict(hits[0])
            if status == "partial" or table is self.chem:
                chosen["matched_name"] = hits[0]["cn"]
            if len(codes) > 1:
                return {"status": "ambiguous", "candidates": hits, "chosen": chosen, "name": name}
            return {"status": status, "candidates": hits, "chosen": chosen, "name": name}
        best, score = None, 0.0
        for k, hits in self.common.items():
            if not k or abs(len(k) - len(key)) > 4:
                continue
            s = difflib.SequenceMatcher(None, key, k).ratio()
            if s > score:
                best, score = hits, s
        if best and score >= 0.9:
            chosen = dict(best[0])
            chosen["matched_name"] = best[0]["cn"]
            chosen["score"] = round(score, 3)
            return {"status": "fuzzy", "candidates": best, "chosen": chosen, "name": name}
        return {"status": "none", "candidates": [], "chosen": None, "name": name}

    def state_of(self, name):
        res = self.lookup(name)
        if res["chosen"] and res["chosen"].get("state"):
            return res["chosen"]["state"]
        if name in self.inorganic:
            return "固体"
        return ""
