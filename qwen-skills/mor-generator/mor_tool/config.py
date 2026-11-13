"""读取 config.yaml 和 rules/。路径一律相对仓库根目录。"""

from pathlib import Path

import yaml

TOOL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOL_DIR.parents[1]


def _yaml(path):
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


class Config:
    def __init__(self, template=None, validation=None):
        self.validation_override = validation
        self.data = _yaml(TOOL_DIR / "config.yaml")
        self.rules_dir = REPO_ROOT / self.data.get("rules_dir", "qwen-skills/mor-generator/rules")
        self.knowledge_dir = REPO_ROOT / self.data.get("knowledge_dir", "qwen-skills/mor-generator/knowledge")
        self.common = _yaml(self.rules_dir / "common.yaml")
        self.sites = _yaml(self.rules_dir / "sites.yaml")
        self.op_mapping = _yaml(self.rules_dir / "op_mapping.yaml")
        self.equipment = _yaml(self.rules_dir / "equipment.yaml") or []
        name = template or self.data.get("default_template", "commercial_validation")
        self.template_name = name
        self.template = _yaml(self.rules_dir / "templates" / ("%s.yaml" % name))

    def resource(self, key):
        override = self.template.get(key + "_path") if self.template else None
        rel = override or self.data["resources"][key]
        p = Path(rel)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def validation(self):
        if self.validation_override is not None:
            return bool(self.validation_override)
        return bool(self.template.get("validation", False))
