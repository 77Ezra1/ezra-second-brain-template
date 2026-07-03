from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate_brain.py"


def load_validate():
    module_name = f"validate_brain_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, VALIDATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_required_tree(root: Path) -> None:
    for path in [
        "README.md",
        "SCHEMA.md",
        "index.md",
        "log.md",
        "config/brain.yaml",
        "config/categories.yaml",
        "wiki/life/index.md",
        "wiki/finance/index.md",
        "wiki/health/index.md",
        "wiki/ideas/index.md",
        "wiki/projects/index.md",
        "wiki/people/index.md",
        "wiki/articles/index.md",
        "wiki/research/index.md",
        "wiki/business-intel/index.md",
        "wiki/travel/index.md",
    ]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Test\n", encoding="utf-8")
    for directory in ["inbox", "raw", "wiki", "reviews", "scripts", "templates"]:
        (root / directory).mkdir(parents=True, exist_ok=True)


def test_validate_success_for_minimal_valid_tree(tmp_path: Path, monkeypatch) -> None:
    validate = load_validate()
    seed_required_tree(tmp_path)
    note = tmp_path / "wiki" / "life" / "daily.md"
    note.write_text(
        "---\n"
        "id: test\n"
        "created: 2026-06-27T00:00:00+08:00\n"
        "updated: 2026-06-27T00:00:00+08:00\n"
        "type: daily\n"
        "category: life\n"
        "tags: [daily]\n"
        "source: pytest\n"
        "confidence: high\n"
        "privacy: private\n"
        "---\n\n# Test Note\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validate, "ROOT", tmp_path)

    assert validate.main() == 0


def test_validate_fails_for_wiki_note_without_frontmatter(tmp_path: Path, monkeypatch) -> None:
    validate = load_validate()
    seed_required_tree(tmp_path)
    bad = tmp_path / "wiki" / "life" / "bad.md"
    bad.write_text("# Missing Frontmatter\n", encoding="utf-8")
    monkeypatch.setattr(validate, "ROOT", tmp_path)

    assert validate.main() == 1
