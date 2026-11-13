# Claude Code Skills · 项目级安装

本目录包含本项目预装的 Claude Code Skills（按 [Agent Skills 标准](https://agentskills.io)），
当你用 Claude Code CLI / 兼容 IDE 打开本项目时会自动加载，无需再装一次。

> **目录约定**：`.claude/skills/<skill-name>/SKILL.md` 是 Claude Code 的项目级 skill 标准路径，
> 跟随 git 仓库分发。本目录所有 skill 均**完整拷贝自上游开源仓库**（含 LICENSE / NOTICE），
> 后续可通过 `git pull` 上游仓库手动升级。

---

## 已安装 Skill 概览

| Skill / Plugin | 子模块 | 触发方式 | 上游仓库 | License |
|---|---|---|---|---|
| **market-research** | 单 skill | 自然语言（"market research / competitor analysis / TAM-SAM-SOM / investor due diligence"） | [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | MIT |
| **document-skills**（4 子 skill） | `docx` · `pdf` · `pptx` · `xlsx` | 自然语言（"use the PDF skill to ..." / "create a docx ..."） | [anthropics/skills](https://github.com/anthropics/skills) | Anthropic source-available（随 Claude 服务使用） |
| **academic-research-skills**（4 子 skill） | `deep-research` · `academic-paper` · `academic-paper-reviewer` · `academic-pipeline` | Slash 命令 `/deep-research` `/academic-paper` `/paper-reviewer` `/academic-pipeline` + 自然语言 | [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | CC BY-NC 4.0（非商业用途） |

---

## 1 · market-research

**来源**：`affaan-m/everything-claude-code/.agents/skills/market-research/` （上游仓库 159K stars）

**做什么**：把"做市场调研"从"写 PPT theater"升级成"附原始来源、含反方证据、给出可执行建议"的结构化产出。

**适用场景**（节选自 SKILL.md `description`）：
- 调研一个市场 / 细分 / 公司 / 投资人 / 技术趋势
- 建 TAM / SAM / SOM 估算
- 竞品 / 相邻产品对比
- 投资人沟通前的尽调材料
- 在进入 / 投资 / 开发某市场前 pressure-test 你的论点

**触发示例**：
> "Help me do market research on the CDMO AI tooling landscape — TAM/SAM/SOM with sources"
> "Competitive analysis of 智现未来 vs 华为云盘古制药 in pharma AI"

**位置**：`.claude/skills/market-research/`

---

## 2 · document-skills（Anthropic 官方 4 件套）

**来源**：`anthropics/skills` 仓库的 `skills/{docx,pdf,pptx,xlsx}/` 四个子目录（135K stars，
本项目里这套是支撑 Claude.ai 文档创建功能的"production AI"实现）。

**做什么**：让 Claude 真正"打开 / 编辑 / 生成" 4 种主流 Office 文件，不是简单文本对话。

| 子 skill | 能力 |
|---|---|
| **docx** | 创建 / 修改 .docx Word 文档，支持样式 / 修订 / 注释（含 `accept_changes.py` `comment.py` 等 Python 脚本） |
| **pdf** | 提取表单字段、内容、bounding box；PDF ↔ 图片转换；表单填充验证 |
| **pptx** | 用 `pptxgenjs` 生成 PowerPoint，含模板编辑能力 |
| **xlsx** | 创建 / 编辑 .xlsx Excel，含公式、格式化、多 sheet |

**触发示例**：
> "Use the PDF skill to extract the form fields from /workspace/some-file.pdf"
> "Create a .docx from this Markdown using the docx skill"
> "Use the pptx skill to turn this outline into a 10-slide deck"

**位置**：`.claude/skills/{docx,pdf,pptx,xlsx}/`

**⚠️ License 注意**：这 4 个 skill 是 **Anthropic source-available 协议**（不是 Apache 2.0），
使用受 Anthropic 服务协议约束。详见各 `LICENSE.txt`。允许跟随 Claude 服务一起使用。

---

## 3 · academic-research-skills（v3.9.4.2）

**来源**：`Imbad0202/academic-research-skills`（11.9K+ stars，作者 Cheng-I Wu）

**做什么**：把"学术研究全流程"包成 4 个相互衔接的 skill —— research → write → review → revise → finalize。

| 子 skill | 能力 |
|---|---|
| **deep-research** | 系统化文献搜索 + source verification（理论扎根 + 跨索引三角校验） |
| **academic-paper** | 12-agent 论文写作（Style Calibration、Writing Quality、LaTeX 加固、可视化、修订指导、引文转换、防泄漏协议、VLM 配图核查） |
| **academic-paper-reviewer** | 7-agent 多视角同行评审（0–100 分 rubric、跨模型 DA 批判 / 校准、R&R traceability matrix） |
| **academic-pipeline** | 10 阶段流水线编排（自适应 checkpoint、声明校验、Material Passport、可选 repro_lock、跨模型 integrity 验证） |

**触发方式**：
```
/deep-research        # 进入深度研究模式
/academic-paper       # 进入论文写作模式
/paper-reviewer       # 进入同行评审模式
/academic-pipeline    # 启动全流程编排
```
也可以用自然语言："review paper / survey / 综述 / write a literature review / 投稿前的同行评议"。

**位置**：`.claude/skills/academic-research-skills/`（含 `commands/` `hooks/` `agents/` `shared/`
`scripts/` `docs/` `examples/` 等共享资源；4 个子 skill 同时存在于 `skills/` 子目录中（symlink））。

**⚠️ License 注意**：**CC BY-NC 4.0 — 仅限非商业用途**。
内部研究 / 学习 / 文献综述 / 非营利项目可以用；如果用于商业出版 / 客户付费交付，需联系作者授权。

---

## 如何使用

### 1. 用 Claude Code CLI 打开本项目

```bash
cd /path/to/this/repo
claude   # 启动 Claude Code 交互
```

Claude Code 会自动扫描 `.claude/skills/` 目录加载所有 SKILL.md，根据用户提问自动激活相应 skill。

### 2. 用 Cursor IDE / Cursor Cloud Agent

Cursor 自有 skill 体系（基于 AGENTS.md），目前**不会自动加载** `.claude/skills/`。
但 Cursor Agent 仍可以**手动读取** `.claude/skills/<skill>/SKILL.md` 来获取 skill 的工作流指引，
作为 prompt 内容供参考。

### 3. 升级 / 卸载

每个 skill 都从对应上游仓库**完整拷贝**进来，并保留了原始 LICENSE。要升级：

```bash
# 例：升级 market-research
cd /tmp && git clone --depth 1 https://github.com/affaan-m/everything-claude-code.git
rm -rf .claude/skills/market-research
cp -r /tmp/everything-claude-code/.agents/skills/market-research .claude/skills/
```

要卸载某个 skill，直接 `rm -rf .claude/skills/<skill-name>/`。

---

## 安装清单（验证用）

```
.claude/skills/
├── README.md                          (本文件)
├── market-research/                   (1 个 SKILL.md, MIT)
│   ├── SKILL.md
│   ├── LICENSE
│   └── agents/openai.yaml
├── docx/                              (Anthropic source-available)
├── pdf/
├── pptx/
├── xlsx/                              (以上 4 个含 SKILL.md + scripts/ + LICENSE.txt)
└── academic-research-skills/          (CC BY-NC 4.0, v3.9.4.2)
    ├── README.md
    ├── LICENSE / NOTICE.md
    ├── deep-research/SKILL.md
    ├── academic-paper/SKILL.md
    ├── academic-paper-reviewer/SKILL.md
    ├── academic-pipeline/SKILL.md
    ├── agents/ commands/ hooks/ scripts/ shared/ docs/ examples/
    ├── skills/  (symlinks to 4 个子 skill)
    ├── .claude/  (上游自带的 plugin 设计文档)
    └── .claude-plugin/  (上游自带的 plugin manifest)
```

共 9 个 SKILL.md（每个子 skill 一份）。

---

*Installed @ 2026-05-22 by Cursor Cloud Agent*
