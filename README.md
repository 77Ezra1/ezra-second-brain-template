# ezra-second-brain-template

A filesystem-first personal second brain template for Telegram/Hermes-style workflows.

It captures raw messages, turns them into structured Markdown knowledge, supports daily reports, lightweight actions, article/document ingestion, expense records, and deterministic local queries — while keeping your data in ordinary files.

> 中文：一个文件系统优先的个人外脑模板。通过 Telegram / CLI 捕获信息，用 Markdown 管理长期知识，支持日报、待办、文章归档、消费记录和本地查询。

## Features

- **Filesystem-first**: Markdown / JSONL files are the source of truth.
- **Low-friction capture**: `外脑：...`, `外脑？...`, `外脑待办：...` style commands.
- **Daily work report**: `今日复盘 / 明日安排` generator.
- **Article ingestion**: URL, pasted text, local documents, WeChat article extraction helpers.
- **Topic pages**: structured knowledge sedimentation under `wiki/topics/`.
- **Lightweight actions**: open / complete / cancel tasks in Markdown.
- **Privacy-first template**: no real user data, no tokens, no external sync enabled by default.

## Quick start

```bash
git clone https://github.com/<your-user>/ezra-second-brain-template.git
cd ezra-second-brain-template
python -m pytest tests -q
python scripts/brain_cli.py validate
```

Create your private data root from the examples:

```bash
cp config/brain.example.yaml config/brain.yaml
mkdir -p data
```

Use an isolated data directory while testing:

```bash
python scripts/telegram_brain_router.py --text "外脑：今天开项目会，确认内容框架" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source telegram --data-dir ./data
```

Generate a demo work report:

```bash
HERMES_SECOND_BRAIN_ROOT=./examples/data python scripts/work_report.py --review-day 2026-01-01 --plan-day 2026-01-02 --no-save
```

## Command examples

```bash
python scripts/telegram_brain_router.py --text "外脑：今天午饭花了28元" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑？这个月主要开销是什么" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑待办：明天整理素材命名规则" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑完成：整理素材命名规则" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑存文章：https://example.com/article" --source telegram --data-dir ./data
```

## Repository layout

```text
config/      Example configuration; copy brain.example.yaml to brain.yaml locally.
scripts/     Deterministic CLI/router/ingestion/validation scripts.
templates/   Markdown templates for notes.
tests/       Pytest suite.
examples/    Fictional sample data only.
docs/        Architecture and privacy notes.
```

Private user data should live in `data/` or another path configured by `HERMES_SECOND_BRAIN_ROOT`; do not commit it.

## Privacy and publishing rules

This template excludes real records. For your own fork:

- Never commit generated private content under `data/`, `raw/`, `inbox/`, `wiki/`, `daily/`, `reviews/`, `.env`, cookies, or tokens. The repository only keeps empty/skeleton index files.
- Keep external sync identifiers in `config/brain.yaml`, which is gitignored.
- Run a secret scan before pushing public changes.

## License

MIT
