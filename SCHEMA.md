# Second Brain Schema

## Frontmatter

除 `index.md`、`README.md`、`log.md` 外，`wiki/` 下的长期笔记应包含 YAML frontmatter。

```yaml
---
id: 20260627-113308-example
created: 2026-06-27T11:33:08+08:00
updated: 2026-06-27T11:33:08+08:00
type: capture
category: life
tags: [life]
source: telegram
confidence: high
privacy: private
related: []
---
```

## Note Types

| type | directory | purpose |
|---|---|---|
| `capture` | `inbox/` / routed wiki | 原始捕获和通用记录 |
| `daily` | `wiki/life/daily/` | 每日生活日志 |
| `expense` | `wiki/finance/expenses/` | 消费记录和月度表 |
| `health` | `wiki/health/` | 睡眠、身体、情绪、运动 |
| `article` | `wiki/articles/sources/` | 文章/网页资料 |
| `idea` | `wiki/ideas/captures/` | 想法、灵感、观点 |
| `project` | `wiki/projects/active/` | 项目上下文 |
| `person` | `wiki/people/` | 人物相关信息 |
| `review` | `reviews/` | 日/周/月复盘 |
| `question` | `reviews/questions/` | AI 反问与用户回答 |
| `decision` | `wiki/life/decisions.md` | 决策记录 |
| `business_signal` | `wiki/business-intel/signals/` | 商业情报信号 |

## Capture Rules

1. 所有 `外脑：` 输入先写入 `raw/telegram/YYYY-MM-DD.jsonl`。
2. 同时写入 `inbox/YYYY-MM-DD.md`，方便人工回看。
3. 再按语义写入一个或多个 `wiki/` 文件。
4. 每次更新追加 `log.md`。
5. 大更新后运行 `python scripts/validate_brain.py`。

## Linking Rules

- 使用 Obsidian 风格 `[[Note Name]]` 表示概念链接。
- 文章、健康、财务、项目之间可互相引用。
- 不确定的关联放入 “Possible Links”，不要当成事实。

## Confidence

- `high`：用户明确提供的事实。
- `medium`：从上下文合理归纳。
- `low`：AI 猜测或需要确认。

## Privacy

- 默认 `privacy: private`。
- 涉及身份证、密码、token、银行卡等不要入库；如用户明确要求，也必须脱敏。
