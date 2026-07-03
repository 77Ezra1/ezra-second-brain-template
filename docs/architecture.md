# Architecture

The core flow is:

```text
raw capture -> inbox -> structured Markdown / JSONL -> deterministic query / reports
```

Key scripts:

- `telegram_brain_router.py`: routes Telegram-style commands.
- `brain_cli.py`: capture, query, article creation, actions, validation entrypoint.
- `work_report.py`: generates concise daily work reports from `daily/work_report.jsonl`.
- `article_url_ingest.py`: fetches and normalizes URL content.
- `validate_brain.py`: validates the filesystem knowledge base.
