# Architecture

The core flow is:

```text
raw capture -> inbox -> structured Markdown / JSONL -> deterministic query / reports
```

Key scripts:

- `install.py`: cross-platform installer; detects or accepts `--platform macos/windows/linux`, writes a platform-aware `config/brain.yaml`, and creates runtime `data/` directories.
- `install-macos.sh`: macOS shell wrapper around `install.py --platform macos`.
- `install-windows.ps1`: Windows PowerShell wrapper around `install.py --platform windows`.
- `telegram_brain_router.py`: routes Telegram-style commands.
- `brain_cli.py`: capture, query, article creation, actions, validation entrypoint.
- `work_report.py`: generates concise daily work reports from `daily/work_report.jsonl`.
- `article_url_ingest.py`: fetches and normalizes URL content.
- `validate_brain.py`: validates the filesystem knowledge base.

Runtime data is intentionally separate from the reusable template. A normal installation writes private records under `data/` and keeps the public repo limited to scripts, tests, docs, templates, examples, and sanitized config examples.
