#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, Any, NamedTuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "article_payload_builder.py"
BRAIN_CLI = ROOT / "scripts" / "brain_cli.py"
ROUTER = ROOT / "scripts" / "telegram_brain_router.py"
WECHAT_MP_EXTRACT = ROOT / "scripts" / "wechat_mp_extract.py"
WECHAT_MP_PLAYWRIGHT_FETCH = ROOT / "scripts" / "wechat_mp_playwright_fetch.py"
ARTICLE_TOPIC_ENRICHER = ROOT / "scripts" / "article_topic_enricher.py"


class ExtractedArticle(NamedTuple):
    title: str
    content: str


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_brain_cli():
    return load_module(BRAIN_CLI, "brain_cli_for_url_ingest")


def fetch_url(url: str, timeout: int = 20) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(urllib.request.url2pathname(parsed.path)).read_text(encoding="utf-8")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "HermesSecondBrainArticleIngest/1.0 (+https://hermes-agent.nousresearch.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec: user-requested URL fetch
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r"(?is)<(script|style|noscript|svg|canvas|form|header|footer|nav|aside)\b.*?</\1>", "\n", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)</(p|div|section|article|h[1-6]|li|blockquote)>", "\n", fragment)
    fragment = re.sub(r"(?is)<[^>]+>", "", fragment)
    text = html.unescape(fragment)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def first_tag_text(markup: str, tag: str) -> str:
    m = re.search(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", markup)
    return strip_tags(m.group(1)).splitlines()[0].strip() if m else ""


def largest_content_block(markup: str) -> str:
    candidates: list[str] = []
    for tag in ["article", "main"]:
        candidates.extend(m.group(1) for m in re.finditer(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", markup))
    if not candidates:
        candidates.extend(m.group(1) for m in re.finditer(r"(?is)<div\b[^>]*(?:class|id)=[\"'][^\"']*(?:article|content|post|entry|main)[^\"']*[\"'][^>]*>(.*?)</div>", markup))
    if not candidates:
        body = re.search(r"(?is)<body\b[^>]*>(.*?)</body>", markup)
        candidates.append(body.group(1) if body else markup)
    return max(candidates, key=lambda s: len(strip_tags(s)))


def html_to_markdown(markup: str, url: str) -> ExtractedArticle:
    clean_markup = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", "\n", markup)
    block = largest_content_block(clean_markup)
    h1 = first_tag_text(block, "h1")
    title = h1 or first_tag_text(clean_markup, "title") or url.rstrip("/").split("/")[-1] or "article"
    content = strip_tags(block)
    if title and not content.startswith(title):
        content = f"# {title}\n\n{content}" if content else f"# {title}"
    elif title and content.startswith(title):
        lines = content.splitlines()
        lines[0] = f"# {title}"
        content = "\n".join(lines)
    return ExtractedArticle(title=title, content=content)


def is_wechat_mp_url(url: str) -> bool:
    return "mp.weixin.qq.com" in urlparse(url).netloc.lower()


def wechat_extract_data(markup: str, url: str) -> dict[str, Any]:
    wx = load_module(WECHAT_MP_EXTRACT, "wechat_mp_extract_for_url_ingest")
    return wx.extract_from_html(markup, url)


def wechat_data_to_article(data: dict[str, Any], url: str) -> ExtractedArticle:
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or data.get("error_code") or "WeChat extraction failed")
    title = data.get("title") or url.rstrip("/").split("/")[-1] or "article"
    return ExtractedArticle(title=title, content=data.get("content") or "")


def wechat_html_to_article(markup: str, url: str) -> ExtractedArticle:
    return wechat_data_to_article(wechat_extract_data(markup, url), url)


def fetch_wechat_with_playwright(url: str, timeout_ms: int = 45000) -> str:
    helper = load_module(WECHAT_MP_PLAYWRIGHT_FETCH, "wechat_mp_playwright_fetch_for_url_ingest")
    return helper.fetch_with_playwright(url, timeout_ms=timeout_ms)


def extract_wechat_with_fallback(url: str, markup: str, playwright_fetcher: Callable[[str], str] | None = None) -> tuple[ExtractedArticle, str]:
    data = wechat_extract_data(markup, url)
    if data.get("ok"):
        return wechat_data_to_article(data, url), "web_extract"
    error_code = data.get("error_code")
    if error_code != "WECHAT_ANTI_BOT":
        raise RuntimeError(data.get("error") or error_code or "WeChat extraction failed")
    playwright_fetcher = playwright_fetcher or fetch_wechat_with_playwright
    browser_markup = playwright_fetcher(url)
    browser_data = wechat_extract_data(browser_markup, url)
    if not browser_data.get("ok"):
        browser_error = browser_data.get("error") or browser_data.get("error_code") or "WeChat Playwright extraction failed"
        raise RuntimeError(f"{data.get('error')}; Playwright fallback failed: {browser_error}")
    return wechat_data_to_article(browser_data, url), "web_extract_playwright"


def enrich_created_article(data_root: Path, result: dict[str, Any]) -> dict[str, Any] | None:
    article_files = [f for f in result.get("files", []) if str(f).startswith("wiki/articles/sources/")]
    if not article_files:
        return None
    enricher = load_module(ARTICLE_TOPIC_ENRICHER, "article_topic_enricher_for_url_ingest")
    old_root = getattr(enricher, "ROOT", ROOT)
    old_article_dir = getattr(enricher, "ARTICLE_DIR", ROOT / "wiki" / "articles" / "sources")
    old_topic_dir = getattr(enricher, "TOPIC_DIR", ROOT / "wiki" / "topics")
    try:
        enricher.ROOT = data_root
        enricher.ARTICLE_DIR = data_root / "wiki" / "articles" / "sources"
        enricher.TOPIC_DIR = data_root / "wiki" / "topics"
        return enricher.enrich_article(data_root / article_files[0])
    finally:
        enricher.ROOT = old_root
        enricher.ARTICLE_DIR = old_article_dir
        enricher.TOPIC_DIR = old_topic_dir


def append_topic_reply(reply_text: str, enrichment: dict[str, Any] | None) -> str:
    if not enrichment or not enrichment.get("topics"):
        return reply_text
    names = [t.get("name", "") for t in enrichment.get("topics", []) if t.get("name")]
    if not names:
        return reply_text
    return reply_text.rstrip() + "\n\n主题：" + "、".join(names)


def fallback_partial(url: str, data_root: Path, source: str, error: str) -> dict[str, Any]:
    brain = load_brain_cli()
    old_root = getattr(brain, "ROOT", ROOT)
    brain.ROOT = data_root
    title = url.rstrip("/").split("/")[-1] or url
    payload = {
        "schema_version": "article-payload-v2",
        "url": url,
        "title": title,
        "source": source,
        "content": None,
        "extraction_status": "partial",
        "extraction_method": "manual_placeholder",
        "extraction_notes": f"URL fetch/extraction failed: {error}",
    }
    data = brain.create_article(url, title=None, content=None, source=source, payload=payload)
    brain.ROOT = old_root
    router = load_module(ROUTER, "router_formatter_for_url_ingest_partial")
    data["reply_text"] = router.format_article(data)
    data["extraction_error"] = error
    data["extraction_notes"] = payload["extraction_notes"]
    return data


def ingest_url(
    url: str,
    *,
    data_root: Path | None = None,
    fetcher: Callable[[str], str] | None = None,
    focus: str = "",
    source: str = "web_extract",
    playwright_fetcher: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    data_root = Path(data_root).resolve() if data_root else ROOT
    fetcher = fetcher or fetch_url
    try:
        markup = fetcher(url)
        method = "web_extract"
        if is_wechat_mp_url(url):
            extracted, method = extract_wechat_with_fallback(url, markup, playwright_fetcher=playwright_fetcher)
        else:
            extracted = html_to_markdown(markup, url)
        min_chars = 10 if is_wechat_mp_url(url) else 20
        if len(extracted.content.strip()) < min_chars:
            raise RuntimeError("extracted content too short")
        builder = load_module(BUILDER, "article_payload_builder_for_url_ingest")
        payload = builder.build_payload(
            url=url,
            title=extracted.title,
            content=extracted.content,
            source=source,
            method=method,
            status="complete",
            focus=focus,
        )
        brain = load_brain_cli()
        old_root = getattr(brain, "ROOT", ROOT)
        brain.ROOT = data_root
        result = brain.create_article(url, payload=payload)
        brain.ROOT = old_root
        enrichment = enrich_created_article(data_root, result)
        if enrichment:
            result["topic_enrichment"] = enrichment
            changed = result.setdefault("files", [])
            for path in enrichment.get("changed", []):
                if path not in changed:
                    changed.append(path)
        formatter = load_module(ROUTER, "router_formatter_for_url_ingest")
        result["reply_text"] = append_topic_reply(formatter.format_article(result), enrichment)
        return result
    except Exception as exc:  # noqa: BLE001 - return honest partial with reason
        return fallback_partial(url, data_root, source="telegram", error=str(exc))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch a URL and ingest it as a complete article-payload-v2 when possible.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--focus", default="")
    args = parser.parse_args(argv)
    result = ingest_url(args.url, data_root=Path(args.data_dir) if args.data_dir else None, focus=args.focus)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
