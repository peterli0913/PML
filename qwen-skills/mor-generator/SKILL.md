---
name: mor-generator
description: 由工艺文件（Tech-*.docx）按 QF05098 MOR 模板、双语单元操作库和物料库生成 MOR 草稿，复核任意版本的 MOR，并从专家定稿的「工艺-MOR」配对和批注中持续学习。Use when 用户说 生成MOR/写MOR/工艺转MOR/MOR草稿/MOR核对/复核MOR/学习MOR/给MOR例子/更新MOR技能。
---

# MOR 生成（mor-generator）

Python 脚本负责所有确定性的工作：解析工艺、查内部控制号、选操作块、组装 Word、复核、学习。
AI（Cursor 或千问里的你）只做脚本做不了的两件事：**补写计划里标成 `needs_ai` 的中英文**，以及**把专家批注提炼成规则或代码改动**。

## 铁律

1. **数字只能来自工艺文件**。温度、时间、用量、限度都按工艺原文写；工艺里没有的，不编，写 `【待补：…】`。
2. **查不到就高亮**。内部控制号只从物料库 xls 或学过的别名表取；查不到、有多个编号、近似匹配的，一律黄色高亮，让人确认。
3. **输出永远是草稿**，按 SOP 由人编写、审核、批准。
4. **不改用户的原始文件**。输出写到新目录。

## 准备

```bash
pip install -r qwen-skills/mor-generator/requirements.txt
# 可选：装 LibreOffice，复核时用来排版并更新「Page X of Y」页码引用
```

资源路径在 `config.yaml`（默认在仓库的 `MOR相关/` 下）：MOR 模板、双语单元操作库、物料库 xls。

## 流程

下面的命令都在仓库根目录执行，`M` 代表 `python qwen-skills/mor-generator/scripts/mor.py`。

### 1. 生成计划

```bash
$M plan 工艺.docx -o out/mor_plan.json            # 非验证项目（默认）
$M --validation yes plan 工艺.docx -o out/mor_plan.json   # 验证项目
```

计划 `mor_plan.json` 是中间产物，人和 AI 都能读：每个 Ins 从哪个工艺操作来、用了哪个例子或库模块、物料和内部控制号、设备、分析方法。末尾的 `todo_summary` 列出：
- `needs_ai`：要你补写的条目路径
- `todo`：要人工填的（客户代码、查不到的内部控制号等）

### 2. AI 补写 `needs_ai`（你来做）

逐条打开 `todo_summary.needs_ai` 里的路径，按下表写一个 `ai_fills.json`，再写回计划：

```bash
$M fill out/mor_plan.json out/ai_fills.json
```

| 路径 | 写什么 | 依据 |
|---|---|---|
| `ins[i].instruction` | `{"cn": …, "en": …}` | `cn` 已按模板规则从工艺转好；有 `example_cn/example_en/example_op_text` 时，对照 `example_op_text` 与 `cn_src` 的差异，**只改变化的部分**，其余照抄例子的写法 |
| `ins[i].safety[j]` | `{"en": …}` | 危害/劳保的英文，参照 `knowledge/glossary.csv` 已有译法 |
| `ins[i].materials[j].en` | 字符串 | 物料英文名，优先物料库英文名 |
| `front.changes[k].en` | 字符串 | 变更说明的英文，和中文逐句对应 |
| `sampling[k].added_en` | `{"检测项": {"test": "EN/中文", "criterion": "EN/中文"}}` | 新增检测项的名称和合格标准，标准按工艺原文 |

`ai_fills.json` 的格式：

```json
[
  {"path": "ins[20].instruction", "value": {"cn": "…", "en": "…"}},
  {"path": "front.changes[0].en", "value": "…"}
]
```

写英文的规则：沿用例子和操作库的句式与术语；数字、单位、符号（≤、~、℃）与中文完全一致；不新增工艺里没有的操作或参数。

### 3. 组装和复核

```bash
$M build out/mor_plan.json -o out/MOR-xxx_草稿.docx
$M check out/MOR-xxx_草稿.docx --tech 工艺.docx --fix --pages
```

或者第 1、3 步一次跑完（AI 补写可以之后再做，重跑 build 即可）：

```bash
$M run 工艺.docx -o out/
```

输出：
- `MOR-xxx_草稿.docx`：粉色槽位已填，填不了的是黄色高亮 `【待补：…】`；蓝色说明已删，红字转黑
- `*.生成报告.docx`：每个 Ins 的来源（哪个例子/哪个库模块）、要人工填写的项、建议核对项
- `*.复核报告.docx`：错误、提示、高亮清单

**所有报告（生成报告、复核报告、对比报告）一律输出 Word（.docx），交给用户的也是 Word，不交 .md。**
你自己需要读报告内容时，命令行已打印摘要；要全文就另跑一次并把 `--report` / `-o` 写成 `.md`，只供你阅读，不交付。

`check` 可以单独用在任何版本的 MOR 上（人工改完也再跑一次）。`--fix` 会：Ins 重新连续编号并同步设备表、原料表、分析方法表里的操作号；操作表首行设为跨页重复标题行；打开文档时更新目录；`--pages` 用 LibreOffice 排版后填「Page X of Y」。正文里「进行操作 8」这类文字引用只报告、不自动改。

把两份报告的要点用中文告诉用户：多少处要人工填、多少处 AI 已补、复核有没有错误。

### 4. 学习：让工具越用越准

专家改完、定稿后，把「工艺 + 定稿 MOR」交给工具学习：

```bash
$M learn 工艺.docx 定稿MOR.docx --id 产品步骤-版本     # 例如 DH313839301-v3
```

学到 `knowledge/`（全是文本文件，可以看 git diff）：

| 文件 | 内容 | 下次怎么用 |
|---|---|---|
| `examples/<id>/ins_XX.xml` | 定稿 MOR 每个 Ins 的原样 Word 块 | 工艺操作相同或相近时直接复用，只改差异 |
| `glossary.csv` | 劳保、危害、标题、物料、设备、整句操作描述的中英文 | 翻译记忆，减少 `needs_ai` |
| `material_aliases.csv` | 工艺写法 → 物料库名称 → 内部控制号 | 例如「36%盐酸」→「试剂盐酸 YL000451」 |
| `op_mapping_learned.yaml` | 工艺操作 → MOR Ins 序列（如 烘料 → 装料 + 烘料） | 拆分方式 |
| `feedback/<id>.md` | 定稿里的专家批注清单 | 你来逐条处理（见下） |
| `learn_log.md` | 每次学了什么 | 追溯 |

学完以后，**逐条处理 `feedback/<id>.md` 里的批注**，按类型落到对应位置，处理完打勾：

| 批注类型 | 改哪里 |
|---|---|
| 通用写法（编号、精度、行数、颜色、安全行过滤） | `rules/common.yaml` |
| 某类操作应该用哪个库模块、怎么拆 | `rules/op_mapping.yaml` |
| 设备名称、用途、计量表 | `rules/equipment.yaml` |
| 厂区地址 | `rules/sites.yaml` |
| 模板差异（验证/非验证、偏好的库标签） | `rules/templates/*.yaml` |
| 规则表达不了的逻辑（新的表格、新的解析） | `mor_tool/*.py`，并在 `tests/` 加一条测试 |
| 只针对这个产品 | 不推广，只在 feedback 里注明 |

改了 Python 或规则后必须跑测试：

```bash
python -m unittest discover -s qwen-skills/mor-generator/tests -v
```

### 5. 衡量效果

```bash
$M compare 生成草稿.docx 人工定稿.docx -o 对比报告.docx
```

报告 Ins 标题一致数、块文字相似度、原料行、内部控制号、设备、分析方法行。新产品的工艺建议先**不学**，生成后和专家定稿对比，再学习，这样每一对都先当一次测试集。

## 目录

```
qwen-skills/mor-generator/
  SKILL.md  PLAN.md  config.yaml  requirements.txt
  scripts/mor.py          命令行入口
  mor_tool/               tech 解析 / materials 物料库 / library 操作库 / plan 计划 / builder 组装
                          checker 复核 / learn 学习 / compare 对比 / knowledge 知识库读写
                          report_docx 报告写成 Word
  rules/                  人维护的规则（YAML）
  knowledge/              学到的知识（自动生成，可人工改）
  tests/                  回归测试
```

## 现在的范围和限制

- 模板：QF05098 v12.0 商业化（验证批）；`--validation yes|no` 切换验证/非验证写法。两份样例都是非验证项目，验证写法只按批注规则实现，尚未与真实验证批 MOR 对比。
- 样例只有 DH313839301 一个产品的 v.2、v.3：同产品升版效果好；新产品（只靠操作库）的初稿要 AI 补的多，需要更多不同产品的配对来学习。
- 设备编号取自流程图，工艺里没有，一律高亮待填。
- 「Page X of Y」按 LibreOffice 排版估算，Word 打开后以 Word 为准。
- 运行方式：现在是脚本 + skill（在 Cursor 或千问里由 AI 执行）；`mor_tool` 的函数已按「计划 JSON 进、docx 出」拆好，以后包成 API 不用改核心逻辑。
