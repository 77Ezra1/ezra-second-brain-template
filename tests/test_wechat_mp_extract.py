from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "scripts" / "wechat_mp_extract.py"
INGEST = ROOT / "scripts" / "article_url_ingest.py"


def load_extractor():
    module_name = f"wechat_mp_extract_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, EXTRACTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_js_content_article_with_metadata() -> None:
    wx = load_extractor()
    html = '''
    <html><head>
      <meta property="og:title" content="公众号旧版文章标题">
      <meta property="og:url" content="https://mp.weixin.qq.com/s/abc">
    </head><body>
      <script>var nickname = htmlDecode("乔木实验室"); var ct = "1780000000";</script>
      <h1 id="activity-name">公众号旧版文章标题</h1>
      <div id="js_content"><p>第一段正文。</p><p><strong>第二段</strong>讲外脑沉淀。</p></div>
      <script nonce="x"></script>
    </body></html>
    '''

    result = wx.extract_from_html(html, "https://mp.weixin.qq.com/s/abc")

    assert result["ok"] is True
    assert result["title"] == "公众号旧版文章标题"
    assert result["author"] == "乔木实验室"
    assert result["published"] != ""
    assert "第一段正文" in result["content"]
    assert "第二段" in result["content"]
    assert result["method"] == "wechat_js_content"


def test_extract_content_noencode_article() -> None:
    wx = load_extractor()
    encoded = r"<section><p>新版沉浸式正文</p><p>包含\u7b2c\u4e8c\u5927\u8111和直播间复盘。</p></section>"
    html = f'''
    <html><head><meta property="og:title" content="新版文章"></head>
    <body><script>window.__INITIAL_STATE__ = {{ content_noencode: '{encoded}' }};</script></body></html>
    '''

    result = wx.extract_from_html(html, "https://mp.weixin.qq.com/s/new")

    assert result["ok"] is True
    assert result["title"] == "新版文章"
    assert "新版沉浸式正文" in result["content"]
    assert "第二大脑" in result["content"]
    assert result["method"] == "wechat_content_noencode"


def test_extract_detects_wechat_verification_page() -> None:
    wx = load_extractor()
    html = "<html><body>当前环境异常，完成验证后即可继续访问 verify.qq.com</body></html>"

    result = wx.extract_from_html(html, "https://mp.weixin.qq.com/s/blocked")

    assert result["ok"] is False
    assert result["error_code"] == "WECHAT_ANTI_BOT"
    assert "当前环境异常" in result["error"]


def test_wechat_extractor_cli_reads_local_html_and_outputs_json(tmp_path: Path) -> None:
    html_file = tmp_path / "wechat.html"
    html_file.write_text(
        '<html><head><meta property="og:title" content="CLI 微信文章"></head><body><div id="js_content"><p>CLI 正文。</p></div><script></script></body></html>',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(EXTRACTOR), "--url", "https://mp.weixin.qq.com/s/cli", "--html-file", str(html_file)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    data = json.loads(completed.stdout)
    assert data["ok"] is True
    assert data["title"] == "CLI 微信文章"
    assert "CLI 正文" in data["content"]


def test_article_url_ingest_uses_wechat_extractor_for_mp_url(tmp_path: Path, monkeypatch) -> None:
    ingest_spec = importlib.util.spec_from_file_location(f"article_url_ingest_wechat_test_{uuid.uuid4().hex}", INGEST)
    assert ingest_spec and ingest_spec.loader
    ingest = importlib.util.module_from_spec(ingest_spec)
    ingest_spec.loader.exec_module(ingest)
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_for_wechat_ingest_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)

    html = '<html><head><meta property="og:title" content="微信入库测试"></head><body><div id="js_content"><p>微信正文讲第二大脑。</p><p>还讲直播间复盘。</p></div><script></script></body></html>'
    result = ingest.ingest_url("https://mp.weixin.qq.com/s/wechat-test", data_root=tmp_path, fetcher=lambda url: html)

    assert result["ok"] is True
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "web_extract"
    assert result["title"] == "微信入库测试"
    raw_path = tmp_path / next(f for f in result["files"] if f.startswith("raw/web/"))
    assert "微信正文讲第二大脑" in raw_path.read_text(encoding="utf-8")


def test_article_url_ingest_uses_playwright_fallback_after_wechat_antibot(tmp_path: Path, monkeypatch) -> None:
    ingest_spec = importlib.util.spec_from_file_location(f"article_url_ingest_wechat_playwright_test_{uuid.uuid4().hex}", INGEST)
    assert ingest_spec and ingest_spec.loader
    ingest = importlib.util.module_from_spec(ingest_spec)
    ingest_spec.loader.exec_module(ingest)
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_for_wechat_playwright_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)

    blocked_html = "<html><body>当前环境异常，完成验证后即可继续访问 verify.qq.com</body></html>"
    browser_html = '<html><head><meta property="og:title" content="浏览器微信文章"></head><body><div id="js_content"><p>Playwright 正文讲第二大脑。</p><p>还讲直播间复盘。</p></div><script></script></body></html>'
    calls: list[str] = []

    def browser_fetch(url: str) -> str:
        calls.append(url)
        return browser_html

    result = ingest.ingest_url(
        "https://mp.weixin.qq.com/s/playwright-test",
        data_root=tmp_path,
        fetcher=lambda url: blocked_html,
        playwright_fetcher=browser_fetch,
    )

    assert calls == ["https://mp.weixin.qq.com/s/playwright-test"]
    assert result["ok"] is True
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "web_extract_playwright"
    assert result["title"] == "浏览器微信文章"
    raw_path = tmp_path / next(f for f in result["files"] if f.startswith("raw/web/"))
    assert "Playwright 正文讲第二大脑" in raw_path.read_text(encoding="utf-8")
