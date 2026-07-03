#!/usr/bin/env python
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOT = ["README.md", "SCHEMA.md", "index.md", "log.md", "config/brain.yaml", "config/categories.yaml"]
REQUIRED_DIRS = ["inbox", "raw", "wiki", "reviews", "scripts", "templates"]
FRONTMATTER_REQUIRED = ["id", "created", "updated", "type", "category", "tags", "source", "confidence", "privacy"]
EXEMPT_NAMES = {"index.md", "README.md"}
EXEMPT_PATHS = {"wiki/health/sleep.md"}  # table log, intentionally no frontmatter for fast append


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") and "\n---\n" in text[4:]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not has_frontmatter(text):
        return {}
    end = text.find("\n---\n", 4)
    block = text[4:end]
    data = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data


def main() -> int:
    errors: list[str] = []
    for item in REQUIRED_ROOT:
        if not (ROOT / item).exists():
            errors.append(f"missing root file: {item}")
    for item in REQUIRED_DIRS:
        if not (ROOT / item).is_dir():
            errors.append(f"missing directory: {item}")

    for md in (ROOT / "wiki").rglob("*.md"):
        r = rel(md)
        text = md.read_text(encoding="utf-8")
        if not text.strip():
            errors.append(f"empty markdown: {r}")
        if md.name in EXEMPT_NAMES or r in EXEMPT_PATHS:
            continue
        fm = parse_frontmatter(text)
        if not fm:
            errors.append(f"missing frontmatter: {r}")
            continue
        for key in FRONTMATTER_REQUIRED:
            if key not in fm:
                errors.append(f"missing frontmatter key {key}: {r}")

    for idx in [
        "wiki/life/index.md", "wiki/finance/index.md", "wiki/health/index.md",
        "wiki/ideas/index.md", "wiki/projects/index.md", "wiki/people/index.md",
        "wiki/articles/index.md", "wiki/research/index.md", "wiki/business-intel/index.md",
        "wiki/travel/index.md",
    ]:
        if not (ROOT / idx).exists():
            errors.append(f"missing category index: {idx}")

    if errors:
        print("Second Brain validation FAILED")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Second Brain validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
