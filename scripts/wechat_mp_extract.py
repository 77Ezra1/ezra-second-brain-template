#!/usr/bin/env python
from __future__ import annotations

import argparse
import datetime as dt
import html as html_lib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
BLOCKED_SIGNALS = ["当前环境异常", "完成验证后即可继续访问", "verify.qq.com", "环境异常"]


def fetch_html(url: str, timeout: int = 30) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(urllib.request.url2pathname(parsed.path)).read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: user-requested URL fetch
        return resp.read().decode("utf-8", errors="replace")


def find_meta(markup: str, name: str) -> str:
    patterns = [
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
    ]
    for pattern in patterns:
        m = re.search(pattern, markup, re.I | re.S)
        if m:
            return html_lib.unescape(m.group(1)).strip()
    return ""


def html_decode_js_value(value: str) -> str:
    return html_lib.unescape(value.replace('\\x26', '&')).strip()


def find_js_string(markup: str, names: list[str]) -> str:
    for name in names:
        patterns = [
            rf'var\s+{re.escape(name)}\s*=\s*["\'](.*?)["\']\s*;',
            rf'var\s+{re.escape(name)}\s*=\s*(?:htmlDecode|JsDecode)\(["\'](.*?)["\']\)\s*;',
            rf'{re.escape(name)}\s*:\s*(?:htmlDecode\(|JsDecode\()?\s*["\'](.*?)["\']',
        ]
        for pattern in patterns:
            m = re.search(pattern, markup, re.S)
            if m:
                return html_decode_js_value(m.group(1))
    return ""


def js_unescape_string(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nx = s[i + 1]
            if nx == "x" and i + 3 < len(s):
                try:
                    out.append(chr(int(s[i + 2:i + 4], 16)))
                    i += 4
                    continue
                except ValueError:
                    pass
            if nx == "u" and i + 5 < len(s):
                try:
                    out.append(chr(int(s[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            out.append({"n": "\n", "t": "\t", "r": "\r", "'": "'", '"': '"', "\\": "\\", "/": "/"}.get(nx, nx))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def extract_content_noencode(markup: str) -> str:
    key = "content_noencode"
    i = markup.find(key)
    if i < 0:
        return ""
    colon = markup.find(":", i)
    if colon < 0:
        return ""
    qpos = -1
    quote = ""
    for j in range(colon + 1, min(len(markup), colon + 100)):
        if markup[j] in ["'", '"']:
            qpos = j
            quote = markup[j]
            break
    if qpos < 0:
        return ""
    buf: list[str] = []
    j = qpos + 1
    while j < len(markup):
        c = markup[j]
        if c == "\\" and j + 1 < len(markup):
            buf.append(c)
            buf.append(markup[j + 1])
            j += 2
            continue
        if c == quote:
            break
        buf.append(c)
        j += 1
    return js_unescape_string("".join(buf))


def strip_to_markdown(fragment: str) -> str:
    fragment = re.sub(r"(?is)<(script|style|noscript|svg|canvas)\b.*?</\1>", "\n", fragment)
    fragment = re.sub(r"(?is)<img\b[^>]*(?:data-src|src)=[\"']([^\"']+)[\"'][^>]*>", lambda m: f"\n![图片]({html_lib.unescape(m.group(1))})\n", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)</(p|div|section|article|h[1-6]|li|blockquote)>", "\n", fragment)
    fragment = re.sub(r"(?is)<[^>]+>", "", fragment)
    text = html_lib.unescape(fragment)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_js_content(markup: str) -> str:
    patterns = [
        r'<div[^>]+id=["\']js_content["\'][^>]*>(.*?)(?:</div>\s*<script|<div\s+class=["\']rich_media_tool|</div>\s*</div>)',
        r'<div[^>]+class=["\'][^"\']*rich_media_content[^"\']*["\'][^>]*>(.*?)(?:</div>\s*<script|<div\s+class=["\']rich_media_tool)',
    ]
    for pattern in patterns:
        m = re.search(pattern, markup, re.I | re.S)
        if m:
            return m.group(1)
    return ""


def unix_to_date(value: str) -> str:
    try:
        return dt.datetime.fromtimestamp(int(value), dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    except Exception:
        return ""


def extract_from_html(markup: str, url: str) -> dict:
    for signal in BLOCKED_SIGNALS:
        if signal in markup:
            return {"ok": False, "url": url, "error_code": "WECHAT_ANTI_BOT", "error": f"WeChat anti-bot verification page detected: {signal}"}

    title = find_meta(markup, "og:title") or find_js_string(markup, ["msg_title"]) or ""
    if not title:
        m = re.search(r'id=["\']activity-name["\'][^>]*>(.*?)</', markup, re.I | re.S)
        if m:
            title = strip_to_markdown(m.group(1))
    author = find_meta(markup, "og:article:author") or find_js_string(markup, ["nickname", "nick_name", "user_name"])
    ct = find_js_string(markup, ["ct", "publish_time"])
    published = unix_to_date(ct) if ct else ""

    body_html = extract_js_content(markup)
    method = "wechat_js_content" if body_html else ""
    if not body_html:
        body_html = extract_content_noencode(markup)
        method = "wechat_content_noencode" if body_html else ""
    if not body_html:
        return {"ok": False, "url": url, "title": title, "author": author, "published": published, "error_code": "WECHAT_CONTENT_NOT_FOUND", "error": "Could not find js_content or content_noencode container."}
    content = strip_to_markdown(body_html)
    if not content:
        return {"ok": False, "url": url, "title": title, "author": author, "published": published, "error_code": "WECHAT_EMPTY_CONTENT", "error": "Extracted WeChat container but content is empty."}
    return {"ok": True, "url": url, "title": title or url.rstrip('/').split('/')[-1], "author": author, "published": published, "content": content, "method": method, "word_count": len(content)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract mp.weixin.qq.com article HTML into JSON, based on qiaomu/weidu public skill strategies.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--html-file")
    args = parser.parse_args(argv)
    if args.html_file:
        markup = Path(args.html_file).read_text(encoding="utf-8", errors="replace")
    else:
        markup = fetch_html(args.url)
    print(json.dumps(extract_from_html(markup, args.url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
