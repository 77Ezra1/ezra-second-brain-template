#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit/push second-brain changes safely")
    parser.add_argument("--push", action="store_true", help="push to origin after commit")
    parser.add_argument("--commit-only", action="store_true", help="commit without push")
    args = parser.parse_args()

    status = run(["git", "status", "--porcelain"])
    if status.returncode != 0:
        print(status.stdout)
        return status.returncode
    if not status.stdout.strip():
        print("no changes")
        return 0
    run(["git", "add", "."])
    msg = "brain: update " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit = run(["git", "commit", "-m", msg])
    print(commit.stdout)
    if commit.returncode != 0:
        return commit.returncode
    if args.push:
        push = run(["git", "push", "origin", "HEAD"])
        print(push.stdout)
        return push.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
