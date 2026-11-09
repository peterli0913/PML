# 约会任务表

建在"企业上下文库"同一个 Base 中，表名为 **约会任务**。

```bash
dws aitable +table-bootstrap --base-id <BASE_ID> --name "约会任务" --fields '[
 {"fieldName":"任务编号","type":"text"},
 {"fieldName":"会议主题","type":"text"},
 {"fieldName":"候选时段","type":"text"},
 {"fieldName":"回复截止","type":"text"},
 {"fieldName":"发送时间","type":"text"},
 {"fieldName":"回复明细","type":"text"},
 {"fieldName":"状态","type":"text"},
 {"fieldName":"日程eventId","type":"text"}
]'
```

建好后，再补两个关联字段（`bidirectionalLink`）：

- `参会人` → 人员表，`multiple: true`
- `关联项目` → 项目卡片，`multiple: true`

## 字段写法

- **任务编号**：`YYYYMMDD-主题缩写`，用户凭此继续任务，例如"继续 20261106-放行评审"。
- **候选时段**：`1=2026-11-12T14:00+08:00/60; 2=…`
- **回复明细**：每人一行，格式为 `姓名 | 必须/建议/可选 | 回复=1,3 | 原文摘要 | 时间`。未回复的写 `未回复(日历:闲/忙)`。
- **状态**：待确认名单 → 等待回复 → 待确认时段 → 已建日程 / 已取消

## 恢复任务

用户说"看看约会回复"或"继续 <任务编号>"时：
1. 读取这条记录；
2. 只对未回复的人执行回查（SKILL.md 的 Step 5-B）；
3. 更新回复明细；
4. 如果已全部回复或已过截止时间，进入 Step 6。
