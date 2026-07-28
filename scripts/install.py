#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import platform
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


def detected_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


def normalize_config_path(path: Path) -> str:
    return str(path.resolve()).replace(os.sep, "/")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    parser = argparse.ArgumentParser(description="Install ezra-second-brain-template into a local second-brain workspace.")
    parser.add_argument("--target", default=os.environ.get("SECOND_BRAIN_HOME", str(DEFAULT_TARGET)), help="Install target directory. Default: ~/second-brain")
    parser.add_argument("--platform", choices=["auto", "macos", "windows", "linux"], default="auto", help="Platform preset for messages and helper files. Default: auto")
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


def ensure_runtime_layout(target: Path, *, platform_name: str = "auto") -> None:
    platform_name = detected_platform() if platform_name == "auto" else platform_name
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
        text = text.replace("root: ./data", f"root: {normalize_config_path(target / 'data')}")
        text = text.replace("platform: auto", f"platform: {platform_name}")
        config.write_text(text, encoding="utf-8")
    elif config.exists():
        text = config.read_text(encoding="utf-8")
        updated = text
        # A freshly copied template config is still generic. Convert only those
        # generic placeholders; preserve existing user-specific configs on --force.
        updated = updated.replace("root: ./data", f"root: {normalize_config_path(target / 'data')}")
        updated = updated.replace("platform: auto", f"platform: {platform_name}")
        if updated != text:
            config.write_text(updated, encoding="utf-8")
    categories = target / "config" / "categories.yaml"
    categories_example = target / "config" / "categories.example.yaml"
    if not categories.exists() and categories_example.exists():
        shutil.copy2(categories_example, categories)


def print_platform_next_steps(target: Path, *, platform_name: str) -> None:
    python_cmd = "py -3" if platform_name == "windows" else "python3"
    activate = ".venv\\Scripts\\Activate.ps1" if platform_name == "windows" else "source .venv/bin/activate"
    cd_cmd = f"cd {target}" if platform_name != "windows" else f"cd {target}"
    print("\nInstalled ezra-second-brain-template successfully.")
    print(f"Workspace: {target}")
    print(f"Platform preset: {platform_name}")
    print("Try:")
    print(f"  {cd_cmd}")
    print(f"  {python_cmd} scripts/telegram_brain_router.py --text \"外脑：今天开项目会，确认内容框架\" --source cli --data-dir ./data")
    print(f"  {python_cmd} scripts/telegram_brain_router.py --text \"外脑？今天记录了什么\" --source cli --data-dir ./data")
    print("Optional virtual environment:")
    print(f"  {python_cmd} -m venv .venv")
    print(f"  {activate}")


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
    platform_name = detected_platform() if args.platform == "auto" else args.platform
    if target.exists() and any(target.iterdir()) and not args.force:
        print(f"Target already exists and is not empty: {target}")
        print("Re-run with --force to merge missing template files without deleting your data.")
        return 2

    source = local_template_root() if args.skip_download else download_template()
    print(f"Installing from: {source}")
    print(f"Installing to:   {target}")
    print(f"Platform preset: {platform_name}")
    copy_tree(source, target, force=args.force)
    ensure_runtime_layout(target, platform_name=platform_name)

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "tests", "-q"], target, optional=True)
    run([sys.executable, "scripts/brain_cli.py", "validate"], target, optional=True)

    print_platform_next_steps(target, platform_name=platform_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
