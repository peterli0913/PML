"""把配置、知识库、操作库、物料库装在一起，供命令行和测试使用。"""

from . import library, materials
from .config import Config
from .knowledge import Knowledge


class Session:
    def __init__(self, template=None, knowledge_dir=None):
        self.cfg = Config(template)
        self.kn = Knowledge(knowledge_dir or self.cfg.knowledge_dir)
        self._modules = None
        self._matlib = None
        self._ppe = None

    @property
    def modules(self):
        if self._modules is None:
            self._modules = library.build_index(self.cfg.resource("library"))
            self._modules += library.template_body_modules(self.cfg.resource("template"))
        return self._modules

    @property
    def matlib(self):
        if self._matlib is None:
            self._matlib = materials.MaterialLibrary(self.cfg.resource("materials"), self.kn.alias_path)
        return self._matlib

    @property
    def ppe_glossary(self):
        if self._ppe is None:
            g = library.ppe_glossary(self.cfg.resource("library"))
            for r in self.kn.glossary:
                if r["kind"] == "ppe_item":
                    g[r["cn"]] = r["en"]
            g.setdefault("正压呼吸器", "positive pressure respirator")
            g.setdefault("氯丁橡胶手套", "neoprene gloves")
            g.setdefault("复合膜手套", "composite film gloves")
            self._ppe = g
        return self._ppe
