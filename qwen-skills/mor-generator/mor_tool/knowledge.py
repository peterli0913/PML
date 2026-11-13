"""学到的知识：译名和句子翻译记忆、物料别名、操作映射、操作块例子、专家批注。

全部是纯文本文件（CSV / YAML / JSON / XML），可以直接打开、修改、提交到 git，每次学习后看 diff。
"""

import csv
import json
import re
from pathlib import Path

import yaml

GLOSSARY_FIELDS = ["kind", "cn", "en", "cn_mor", "source", "count"]
ALIAS_FIELDS = ["工艺写法", "物料库名称", "内部控制号", "英文名", "来源"]


def norm_key(s):
    s = (s or "").replace("（", "(").replace("）", ")").replace("，", ",").replace("：", ":").replace("；", ";")
    return re.sub(r"\s+", "", s).strip("。.")


class Knowledge:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "examples").mkdir(exist_ok=True)
        (self.root / "feedback").mkdir(exist_ok=True)
        self.glossary_path = self.root / "glossary.csv"
        self.alias_path = self.root / "material_aliases.csv"
        self.mapping_path = self.root / "op_mapping_learned.yaml"
        self.log_path = self.root / "learn_log.md"
        self.glossary = self._read_csv(self.glossary_path, GLOSSARY_FIELDS)
        self.aliases = self._read_csv(self.alias_path, ALIAS_FIELDS)
        self.mapping = yaml.safe_load(self.mapping_path.read_text(encoding="utf-8")) if self.mapping_path.exists() else {}
        self.mapping = self.mapping or {}

    @staticmethod
    def _read_csv(path, fields):
        if not Path(path).exists():
            return []
        with open(path, encoding="utf-8") as f:
            return [dict(r) for r in csv.DictReader(f)]

    @staticmethod
    def _write_csv(path, rows, fields):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fields})

    def save(self):
        self.glossary.sort(key=lambda r: (r["kind"], r["cn"]))
        self._write_csv(self.glossary_path, self.glossary, GLOSSARY_FIELDS)
        self._write_csv(self.alias_path, self.aliases, ALIAS_FIELDS)
        self.mapping_path.write_text(yaml.safe_dump(self.mapping, allow_unicode=True, sort_keys=True), encoding="utf-8")

    def add_term(self, kind, cn, en, source, cn_mor=""):
        cn, en = (cn or "").strip(), (en or "").strip()
        if not cn or not en:
            return False
        key = norm_key(cn)
        for r in self.glossary:
            if r["kind"] == kind and norm_key(r["cn"]) == key:
                if r["en"] != en and en:
                    r["en"] = en
                if cn_mor:
                    r["cn_mor"] = cn_mor
                r["count"] = str(int(r.get("count") or 1) + 1)
                if source not in r["source"]:
                    r["source"] = (r["source"] + "; " + source).strip("; ")
                return False
        self.glossary.append({"kind": kind, "cn": cn, "en": en, "cn_mor": cn_mor, "source": source, "count": "1"})
        return True

    def term(self, kind, cn):
        key = norm_key(cn)
        for r in self.glossary:
            if r["kind"] == kind and norm_key(r["cn"]) == key:
                return r
        return None

    def add_alias(self, process_name, lib_name, control_no, en, source):
        for r in self.aliases:
            if norm_key(r["工艺写法"]) == norm_key(process_name):
                changed = r["内部控制号"] != control_no
                r.update({"物料库名称": lib_name or r["物料库名称"], "内部控制号": control_no, "英文名": en or r["英文名"]})
                if source not in r["来源"]:
                    r["来源"] = (r["来源"] + "; " + source).strip("; ")
                return changed
        self.aliases.append({"工艺写法": process_name, "物料库名称": lib_name, "内部控制号": control_no, "英文名": en, "来源": source})
        return True

    def add_mapping(self, op_name, sequence, source):
        seq = [{"title_en": a, "title_cn": b} for a, b in sequence]
        entry = self.mapping.setdefault(op_name, {"variants": []})
        for v in entry["variants"]:
            if v["sequence"] == seq:
                v["count"] = v.get("count", 1) + 1
                if source not in v["sources"]:
                    v["sources"].append(source)
                return False
        entry["variants"].append({"sequence": seq, "count": 1, "sources": [source]})
        return True

    def mapping_for(self, op_name):
        entry = self.mapping.get(op_name)
        if not entry or not entry.get("variants"):
            return None
        best = max(entry["variants"], key=lambda v: v.get("count", 1))
        return [(x["title_en"], x["title_cn"]) for x in best["sequence"]]

    def example_dirs(self):
        return sorted(p for p in (self.root / "examples").iterdir() if p.is_dir())

    def load_examples(self):
        out = []
        for d in self.example_dirs():
            idx = d / "index.json"
            if idx.exists():
                data = json.loads(idx.read_text(encoding="utf-8"))
                for item in data["ins"]:
                    item["pair_id"] = data["pair_id"]
                    item["dir"] = str(d)
                    out.append(item)
        return out

    def log(self, text):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n\n")
