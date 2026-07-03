#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- AUTO-INDEX:START -->"
END = "<!-- AUTO-INDEX:END -->"


def title_for(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def replace_block(text: str, body: str) -> str:
    if START in text and END in text:
        before = text.split(START, 1)[0]
        after = text.split(END, 1)[1]
        return before + START + "\n" + body.strip() + "\n" + END + after
    return text.rstrip() + "\n\n" + START + "\n" + body.strip() + "\n" + END + "\n"


def main() -> int:
    wiki_files = [p for p in (ROOT / "wiki").rglob("*.md") if p.name != "index.md"]
    lines = []
    for p in sorted(wiki_files, key=lambda x: rel(x).lower()):
        lines.append(f"- [{title_for(p)}]({rel(p)}) — `{rel(p)}`")
    idx = ROOT / "index.md"
    text = idx.read_text(encoding="utf-8")
    idx.write_text(replace_block(text, "\n".join(lines) if lines else "暂无笔记。"), encoding="utf-8")
    print(f"rebuilt index with {len(lines)} wiki notes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
