# 贡献指南

感谢你愿意改进 `ezra-second-brain-template`。

这个项目是一套**给 AI Agent 用的本地优先外脑**。用户应该可以在 Hermes、Claude Code、Codex、Cursor Agent、本地脚本或自己的 Agent 工作流里使用它，也可以通过 Telegram、飞书、CLI、桌面聊天等自己习惯的入口和 Agent 对话。

写文档或提 PR 时，请保持表达自然、面向用户：这是一个 Agent 可用的本地记忆系统，不是 Telegram 专用机器人，也不是托管式笔记 App。

## 欢迎哪些 PR？

| 类型 | 示例 |
|---|---|
| `docs` | README、命令示例、架构文档、隐私文档 |
| `fix` | 解析 bug、校验 bug、安装器边界问题 |
| `feat` | 新的本地命令、入库流程、主题/查询能力 |
| `test` | 回归测试、fixtures、安装 smoke test |
| `refactor` | 不改变行为的内部整理 |
| `ci` | 测试/校验自动化 |

优先提交小而聚焦的 PR。如果一个改动横跨多个子系统，尽量拆开，除非这些改动必须一起发布。

## 核心原则

### 1. 本地优先，可检查

用户的私人数据应该保存在用户自己控制的文件里：

```text
Markdown + JSONL + deterministic scripts
```

不要把不透明数据库、强依赖云服务或托管平台变成核心必需基础设施。

可选集成可以有，但必须保持可选。

### 2. 能在多种 Agent 和入口里使用

用户应该可以把这套系统装进任意有 shell 能力的 Agent 工作流，然后通过自己习惯的入口记录和查询。

推荐表达：

```text
可以在 Hermes、Claude Code、Codex、Cursor Agent、本地脚本或你自己的 Agent 中使用；也可以通过 Telegram、飞书、CLI、桌面聊天或你接入的任何界面和 Agent 对话。
```

如果提到 `telegram_brain_router.py`，简单说它是当前的**聊天命令路由器**即可。除非文档是在讲集成内部实现，不要过度解释概念。

除非示例专门讲 Telegram，否则 demo 推荐用 `--source cli`。

### 3. 默认保护隐私

不要提交真实个人数据、凭据或外部同步 ID。

不要提交：

- 真实的 `raw/`、`inbox/`、`wiki/`、`daily/`、`reviews/` 或生成的私人记录；
- 真实 Telegram / 飞书 / Lark / GitHub token；
- `.env`、cookie、浏览器 session、API key；
- 真实飞书 Base token、table id、app secret；
- 真实消费记录、工作日报、文章归档、私人行动项。

示例数据请放在 `examples/data/`，测试 fixtures 放在 `tests/fixtures/`，并确保内容是虚构的、可公开的。

### 4. 确定性优先于模糊推理

对于日报、消费、日程、已知主题查询等常见任务，优先使用确定性脚本和测试，而不是完全依赖 LLM 模糊猜测。

好的改动应该能被 Agent 或维护者用命令明确验证。

## 开发环境

克隆仓库：

```bash
git clone https://github.com/77Ezra1/ezra-second-brain-template.git
cd ezra-second-brain-template
```

推荐运行环境：

- Python 3.11+
- Node.js/npm 主要用于 `npx` 安装器包装和 npm scripts

运行验证：

```bash
npm run test
npm run validate
```

等价的直接命令：

```bash
python -m pytest tests -q
python scripts/brain_cli.py validate
```

## 分支和提交规范

分支名建议简短明确：

```text
docs/contributing-guide
fix/expense-parser
feat/topic-query-route
test/installer-smoke
```

提交信息尽量使用 Conventional Commits：

```text
docs: add contributing guide
fix: parse multi-expense messages with unitless amounts
test: cover installer skip-download path
feat: add deterministic topic section query
```

推荐类型：

```text
feat | fix | docs | test | refactor | ci | chore | perf
```

## PR checklist

提 PR 前，请确认：

- [ ] PR 足够聚焦，标题清楚。
- [ ] 改动保持 local-first 和 agent-friendly。
- [ ] 文案能自然说明：用户可以在多种 Agent 工作流和入口中使用这套系统。
- [ ] 没有提交真实私人数据、凭据、token、cookie 或同步 ID。
- [ ] README/docs 示例不会让项目看起来像 Telegram 专用。
- [ ] 新行为有测试；如果没有测试，需要说明原因。
- [ ] `npm run test` 通过。
- [ ] `npm run validate` 通过。
- [ ] 安装器相关改动做过 smoke test。
- [ ] 公开示例只使用虚构数据。

## 不同改动的最低验证要求

| 改动类型 | 最低验证 |
|---|---|
| 纯文档 | `npm run validate`，并检查表达是否自然、定位是否准确 |
| README / 定位 | 确认文案自然、Agent 可用、不像 Telegram 专用；运行 `npm run validate` |
| Python 脚本 | `python -m pytest tests -q` 和 `python scripts/brain_cli.py validate` |
| router / capture 行为 | 新增或更新 router/CLI 测试；用 `--source test` 或 `--source cli` 验证 |
| 安装器 | 同时运行 Python 和 Node 安装 smoke test |
| 飞书/Lark 文档或同步 | 确保全部是占位符，不提交真实 Base/table/app ID |
| 模板数据 | 确认示例数据是虚构且公开安全的 |

推荐安装器 smoke test：

```bash
rm -rf /tmp/esb-verify-python /tmp/esb-verify-node
python scripts/install.py --skip-download --target /tmp/esb-verify-python --skip-tests --force
test -f /tmp/esb-verify-python/config/brain.yaml
test -d /tmp/esb-verify-python/data/raw
python /tmp/esb-verify-python/scripts/telegram_brain_router.py \
  --text '外脑：验证记录' \
  --source test \
  --data-dir /tmp/esb-verify-python/data
node scripts/install-node.js --skip-download --target /tmp/esb-verify-node --skip-tests --force
test -f /tmp/esb-verify-node/config/brain.yaml
test -d /tmp/esb-verify-node/data/raw
```

## 敏感字面量扫描

推送公开改动前，请扫描明显的私人标记。至少检查真实 token 前缀和已知私人 ID。

示例：

```bash
python - <<'PY'
from pathlib import Path
# 用字符串拼接避免这个示例命中自身。
bad = [
    'gh' + 'p_',
    'github' + '_pat_',
    'FEISHU_APP' + '_SECRET=',
    'LARK_APP' + '_SECRET=',
    'TELEGRAM_BOT' + '_TOKEN=',
    'A5' + 'oU',
    'tbl' + 'mln',
    '77Ezra1/' + 'second-brain',
]
for path in Path('.').rglob('*'):
    if path.is_dir() or '.git' in path.parts:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    hits = [marker for marker in bad if marker in text]
    if hits:
        raise SystemExit(f'{path}: {hits}')
print('sensitive_literal_scan=passed')
PY
```

这不是完整的 secret scanner。请结合常识判断，不要提交任何私人信息。

## PR 描述模板

建议按这个结构写：

```markdown
## Summary
- 改了什么？
- 为什么需要？

## Positioning / privacy check
- [ ] 保持 local-first
- [ ] 能说明项目可用于多种 Agent 和入口
- [ ] 不包含私人数据或密钥

## Verification
- [ ] npm run test
- [ ] npm run validate
- [ ] 如果涉及安装器，已运行 smoke test

## Notes
其他 reviewer 需要知道的信息。
```

## Review 标准

如果 PR 出现以下问题，可能会被要求修改：

- 让项目看起来像 Telegram 专用；
- 核心本地使用必须依赖云服务；
- 引入私人数据或过于真实的个人示例；
- 行为变更没有测试；
- 让确定性查询变得更模糊、更依赖 LLM 猜测；
- 破坏安装或验证流程；
- 引入维护成本很高的工作流概念，把项目变成 Jira/Notion。

## 维护者合并前检查

合并前，维护者应至少验证：

```bash
npm run test
npm run validate
```

如果改动涉及安装器或脚本，也要运行上面的 smoke test。

贡献者 PR 推荐 squash merge，保持主分支历史清晰。
