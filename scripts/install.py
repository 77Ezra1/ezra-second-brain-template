#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ZIP_URL = "https://github.com/77Ezra1/ezra-second-brain-template/archive/refs/heads/master.zip"
DEFAULT_TARGET = Path.home() / "second-brain"
EXCLUDE_NAMES = {".git", "__pycache__", ".pytest_cache", "node_modules", "data"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    parser = argparse.ArgumentParser(description="Install ezra-second-brain-template into a local second-brain workspace.")
    parser.add_argument("--target", default=os.environ.get("SECOND_BRAIN_HOME", str(DEFAULT_TARGET)), help="Install target directory. Default: ~/second-brain")
    parser.add_argument("--force", action="store_true", help="Allow installing into a non-empty directory; existing files are preserved unless template files are missing.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest after installation.")
    parser.add_argument("--skip-download", action="store_true", help="Use the current repository checkout instead of downloading GitHub zip. Useful for local development.")
    return parser.parse_args(argv)


def copy_tree(src: Path, dst: Path, *, force: bool = False) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in EXCLUDE_NAMES:
            continue
        if item.suffix in EXCLUDE_SUFFIXES:
            continue
        target = dst / item.name
        if item.is_dir():
            copy_tree(item, target, force=force)
        else:
            if target.exists() and not force:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def download_template() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ezra-second-brain-template-"))
    archive = tmp / "template.zip"
    print(f"Downloading template from {REPO_ZIP_URL}")
    urllib.request.urlretrieve(REPO_ZIP_URL, archive)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(tmp)
    roots = [p for p in tmp.iterdir() if p.is_dir() and p.name.startswith("ezra-second-brain-template-")]
    if not roots:
        raise RuntimeError("Downloaded archive did not contain expected repository root.")
    return roots[0]


def local_template_root() -> Path:
    # install.py lives under scripts/ in a normal checkout. If executed via `python -c exec(...)`,
    # __file__ may not point to a real repo; fall back to download in that case.
    here = Path(globals().get("__file__", "")).resolve()
    candidate = here.parents[1] if here and len(here.parents) >= 2 else None
    if candidate and (candidate / "scripts" / "brain_cli.py").exists() and (candidate / "README.md").exists():
        return candidate
    return download_template()


def ensure_runtime_layout(target: Path) -> None:
    for rel in [
        "data/raw",
        "data/inbox",
        "data/wiki/life",
        "data/wiki/finance",
        "data/wiki/health",
        "data/wiki/ideas",
        "data/wiki/projects",
        "data/wiki/people",
        "data/wiki/articles",
        "data/wiki/research",
        "data/wiki/business-intel",
        "data/wiki/travel",
        "data/daily/reports",
        "data/reviews",
    ]:
        (target / rel).mkdir(parents=True, exist_ok=True)
    config = target / "config" / "brain.yaml"
    example = target / "config" / "brain.example.yaml"
    if not config.exists() and example.exists():
        text = example.read_text(encoding="utf-8")
        text = text.replace("root: ./data", f"root: {str((target / 'data').resolve()).replace(os.sep, '/')}")
        config.write_text(text, encoding="utf-8")
    categories = target / "config" / "categories.yaml"
    categories_example = target / "config" / "categories.example.yaml"
    if not categories.exists() and categories_example.exists():
        shutil.copy2(categories_example, categories)


def run(cmd: list[str], cwd: Path, *, optional: bool = False) -> int:
    print("$ " + " ".join(cmd))
    try:
        completed = subprocess.run(cmd, cwd=cwd, text=True, check=False)
    except FileNotFoundError:
        if optional:
            print(f"Skipped: command not found: {cmd[0]}")
            return 127
        raise
    if completed.returncode != 0 and not optional:
        raise SystemExit(completed.returncode)
    return completed.returncode


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not args.force:
        print(f"Target already exists and is not empty: {target}")
        print("Re-run with --force to merge missing template files without deleting your data.")
        return 2

    source = local_template_root() if args.skip_download else download_template()
    print(f"Installing from: {source}")
    print(f"Installing to:   {target}")
    copy_tree(source, target, force=args.force)
    ensure_runtime_layout(target)

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "tests", "-q"], target, optional=True)
    run([sys.executable, "scripts/brain_cli.py", "validate"], target, optional=True)

    print("\nInstalled ezra-second-brain-template successfully.")
    print(f"Workspace: {target}")
    print("Try:")
    print(f"  cd {target}")
    print('  python scripts/telegram_brain_router.py --text "外脑：今天开项目会，确认内容框架" --source telegram --data-dir ./data')
    print('  python scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source telegram --data-dir ./data')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
