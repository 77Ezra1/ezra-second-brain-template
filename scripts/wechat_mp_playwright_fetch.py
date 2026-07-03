#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def bundled_browser_candidates() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    return [
        local / "ms-playwright" / "chromium_headless_shell-1223" / "chrome-headless-shell-win64" / "chrome-headless-shell.exe",
        local / "ms-playwright" / "chromium-1223" / "chrome-win" / "chrome.exe",
    ]


def fetch_with_playwright(url: str, timeout_ms: int = 45000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        completed = subprocess.run(
            ["uv", "run", "--with", "playwright", "python", str(__file__), "--url", url, "--timeout-ms", str(timeout_ms)],
            text=True,
            capture_output=True,
            check=True,
        )
        return completed.stdout

    with sync_playwright() as p:
        launch_options = {"headless": True}
        chrome = getattr(p.chromium, "executable_path", None)
        candidates = [Path(chrome)] if chrome else []
        candidates.extend(bundled_browser_candidates())
        for chrome_path in candidates:
            try:
                if chrome_path.exists():
                    launch_options["executable_path"] = str(chrome_path)
                    break
            except OSError:
                continue
        browser = p.chromium.launch(**launch_options)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
            )
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_selector("#js_content, .rich_media_content", timeout=15000)
            except Exception:
                # Keep the loaded HTML even if WeChat serves an anti-bot or changed layout page.
                pass
            return page.content()
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch mp.weixin.qq.com HTML with Playwright Chromium fallback.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    args = parser.parse_args(argv)
    html = fetch_with_playwright(args.url, args.timeout_ms)
    sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
