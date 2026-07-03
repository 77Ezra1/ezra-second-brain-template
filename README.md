# ezra-second-brain-template

> A filesystem-first second brain for Telegram / Hermes / any agent that can run a shell.

`ezra-second-brain-template` turns chat-style notes into a local, inspectable Markdown knowledge base. It captures raw messages, structures them into notes, actions, expenses, articles, topics, and daily reports — while keeping your private data in ordinary files that you own.

[中文说明](README.zh-CN.md) · [Command list / 命令清单](docs/commands.zh-CN.md)

## The vibe

Most note systems ask you to open an app, pick a database, choose tags, and maintain a workflow.

This one starts with a sentence:

```text
外脑：今天开项目会，确认内容框架和下周安排
```

Then it turns that sentence into a local trail:

```text
raw input -> inbox -> structured Markdown / JSONL -> query / review / daily report
```

The goal is not to replace Notion or a project-management system. The goal is to give your agent a durable local memory layer that is:

- boring enough to last;
- transparent enough to debug;
- private enough to trust;
- flexible enough to remix.

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
| Agent install | Let any shell-capable agent bootstrap it | Python one-liner / `npx` |

## Install it like an agent would

Give this block to any coding agent — Hermes, Claude Code, Codex, Cursor Agent, etc.:

```text
Install ezra-second-brain-template for me. Create a local second-brain workspace, do not overwrite existing private data, fetch the template from https://github.com/77Ezra1/ezra-second-brain-template, copy config/brain.example.yaml to config/brain.yaml, create local data directories, run tests/validation, and tell me the install path and commands. If you can run shell commands, prefer:
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

```bash
cd ~/second-brain

python scripts/telegram_brain_router.py \
  --text "外脑：今天开项目会，确认内容框架" \
  --source telegram \
  --data-dir ./data

python scripts/telegram_brain_router.py \
  --text "外脑？今天记录了什么" \
  --source telegram \
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
