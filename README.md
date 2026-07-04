# ezra-second-brain-template

> A local-first memory layer for AI agents — usable from Telegram, CLI, Hermes, Claude Code, Codex, Cursor Agent, or any tool that can run shell commands.

`ezra-second-brain-template` turns lightweight natural-language inputs into a local, inspectable Markdown/JSONL knowledge base. It preserves raw inputs, structures them into notes, actions, expenses, articles, topics, and daily reports, and keeps your private data in ordinary files that you own.

**Important:** Telegram is only one possible communication channel. It is not the agent. The actual workflow is designed around an agent + local filesystem + deterministic scripts. Telegram, Feishu/Lark, a desktop chat, a terminal, or another app can all act as input/output surfaces.

[中文说明](README.zh-CN.md) · [Command list / 命令清单](docs/commands.zh-CN.md)

## Mental model

```text
Any input channel
  Telegram / CLI / Hermes / Claude Code / Codex / Cursor / Feishu / your own app
        ↓
Agent or script router
        ↓
Raw input preserved
        ↓
Structured Markdown + JSONL
        ↓
Deterministic query / review / daily report / downstream sync
```

The project is **not** a Telegram bot template and not a heavy Notion/Jira replacement. It is a portable local memory substrate that agents can read, write, validate, and migrate.

## Why this exists

Most personal knowledge systems fail in one of three ways:

- capture is too heavy, so notes never get written;
- data is trapped in a product database;
- agents can chat, but they do not have a stable local memory layer they can inspect and maintain.

This template takes the opposite path:

- **light capture** — say one sentence from any channel;
- **plain storage** — Markdown + JSONL instead of opaque app state;
- **deterministic retrieval** — common queries use scripts/rules before fuzzy LLM search;
- **agent-friendly maintenance** — tests, validation, schemas, and installer scripts are included;
- **local ownership** — private records stay in your workspace, not in the public template.

## What it can do

| Capability | What it means | Example |
|---|---|---|
| Quick capture | Preserve raw input and write readable notes | `外脑：今天开项目会` |
| Deterministic query | Answer from local files before vague search | `外脑？今天记录了什么` |
| Daily work report | Generate `今日复盘 / 明日安排` | `python scripts/work_report.py --review-day today` |
| Lightweight actions | Open / complete / cancel Markdown tasks | `外脑待办：统一素材命名规则` |
| Article ingestion | Save URLs, pasted articles, local docs | `外脑存文章：https://example.com/article` |
| Topic sedimentation | Build durable topic pages over time | `外脑？人设IP 方法论` |
| Expense capture | Lightweight bookkeeping in Markdown | `外脑：今天午饭花了28元` |
| Agent bootstrap | Let any shell-capable agent install and verify it | Python one-liner / `npx` |
| Optional cloud sync | Push selected local data into Feishu/Lark dashboards | `lark-cli` integration |

## Channels vs agents

This distinction matters:

| Layer | Examples | Role |
|---|---|---|
| **Agent** | Hermes, Claude Code, Codex, Cursor Agent, your custom agent | Understands intent, calls scripts, edits files, verifies results |
| **Channel** | Telegram, Feishu/Lark, desktop chat, terminal, web app | Where the user sends commands and receives answers |
| **Memory layer** | This repository's Markdown/JSONL files and scripts | Durable local storage + deterministic operations |

So when you see `telegram_brain_router.py`, read it as a **chat-command router**. It exists because Telegram-style messages are a convenient mobile input format, but the same commands can be sent by any agent or CLI.

## Install it like an agent would

Give this block to any coding agent — Hermes, Claude Code, Codex, Cursor Agent, etc.:

```text
Install ezra-second-brain-template for me. Create a local second-brain workspace, do not overwrite existing private data, fetch the template from https://github.com/77Ezra1/ezra-second-brain-template, copy config/brain.example.yaml to config/brain.yaml, create local data directories, run tests/validation, and tell me the install path and commands. Treat Telegram as an optional communication channel, not as the agent or the core product.

If you can run shell commands, prefer:
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
```

Or run it yourself:

```bash
# Universal Python one-liner
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"

# Custom target
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --target ~/second-brain

# Node/npm style
npx github:77Ezra1/ezra-second-brain-template --target ~/second-brain
```

> The `npx` path calls the Python installer internally, so Python 3.11+ is still recommended.

## 10-second demo

The demo uses the router script because it understands chat-style commands. `--source cli` marks this demo input as coming from the command line; you can change the source to `telegram`, `hermes`, `cursor`, `feishu`, or another label for your own integration.

```bash
cd ~/second-brain

python scripts/telegram_brain_router.py \
  --text "外脑：今天开项目会，确认内容框架" \
  --source cli \
  --data-dir ./data

python scripts/telegram_brain_router.py \
  --text "外脑？今天记录了什么" \
  --source cli \
  --data-dir ./data
```

Generate a demo daily report:

```bash
HERMES_SECOND_BRAIN_ROOT=./examples/data \
python scripts/work_report.py --review-day 2026-01-01 --plan-day 2026-01-02 --no-save
```

Output:

```text
1/1 今日复盘
1. 开项目会确认内容框架

1/2 明日安排
1. 暂无记录
```

## Command examples

| You want to... | Say / run |
|---|---|
| Capture a note | `外脑：今天完成了素材复盘` |
| Ask about today | `外脑？今天记录了什么` |
| Ask about expenses | `外脑？这个月主要开销是什么` |
| Save an article | `外脑存文章：https://example.com/article` |
| Add an action | `外脑待办：统一素材命名规则` |
| Complete an action | `外脑完成：统一素材命名规则` |
| Summarize | `外脑总结：今天` |
| Generate questions | `外脑提问：最近一周` |
| Correct a record | `外脑修正：把午饭28改成32` |

See the full list: [`docs/commands.zh-CN.md`](docs/commands.zh-CN.md)

## Optional: Feishu / Lark cloud docs and Base dashboards

The core template is local-first. If you also install `lark-cli`, agents can connect this workflow to Feishu/Lark Docs and Base tables:

- sync selected expenses, reports, or project metrics into Base;
- build category dashboards and trend charts;
- read or create cloud documents for collaboration.

```bash
npm install -g @larksuite/cli
npx -y skills add https://open.feishu.cn --skill -y
lark-cli --version
```

Chinese setup guide: [`docs/feishu-lark-cli.zh-CN.md`](docs/feishu-lark-cli.zh-CN.md)

## Repository layout

```text
config/      Example configuration; copy brain.example.yaml to brain.yaml locally.
scripts/     Deterministic CLI/router/ingestion/validation scripts.
templates/   Markdown templates for notes.
tests/       Pytest suite.
examples/    Fictional sample data only.
docs/        Architecture, privacy, command list.
```

Private user data should live in `data/` or another path configured by `HERMES_SECOND_BRAIN_ROOT`; do not commit it.

## Privacy rules

This template excludes real records. For your own fork:

- never commit generated private content under `data/`, `raw/`, `inbox/`, `wiki/`, `daily/`, `reviews/`;
- never commit `.env`, cookies, tokens, credentials, or external sync IDs;
- keep real config in a local-only config file;
- run a sensitive literal scan before pushing public changes.

## Development

```bash
npm run test
npm run validate

# or directly
python -m pytest tests -q
python scripts/brain_cli.py validate
```

## License

MIT
