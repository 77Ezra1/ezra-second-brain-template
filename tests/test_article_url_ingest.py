from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts" / "article_url_ingest.py"


def load_ingest():
    module_name = f"article_url_ingest_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, INGEST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, body: str, status: int = 200, url: str = "https://example.com/article") -> None:
        self._body = body.encode("utf-8")
        self.status = status
        self.url = url

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_html_to_markdown_extracts_title_article_and_removes_noise() -> None:
    ingest = load_ingest()
    html = """
    <html><head><title>网页标题</title><script>bad()</script><style>.x{}</style></head>
    <body><nav>导航</nav><article><h1>文章标题</h1><p>第一段正文。</p><p>第二段讲 Wiki 沉淀。</p></article></body></html>
    """

    extracted = ingest.html_to_markdown(html, "https://example.com/a")

    assert extracted.title == "文章标题"
    assert "第一段正文。" in extracted.content
    assert "第二段讲 Wiki 沉淀。" in extracted.content
    assert "bad()" not in extracted.content
    assert "导航" not in extracted.content


def test_ingest_url_complete_with_injected_fetcher_writes_payload_article(tmp_path: Path, monkeypatch) -> None:
    ingest = load_ingest()
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_for_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)

    html = """
    <html><head><title>Fallback Title</title></head>
    <body><article><h1>真实 URL 抓取测试</h1><p>正文讲第二大脑和 Wiki 沉淀。</p><p>也讲直播间投流复盘。</p></article></body></html>
    """

    result = ingest.ingest_url(
        "https://example.com/real-url",
        data_root=tmp_path,
        fetcher=lambda url: html,
        focus="直播间投流复盘启发",
    )

    assert result["ok"] is True
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "web_extract"
    assert result["title"] == "真实 URL 抓取测试"
    assert result["word_count"] > 0
    raw_path = tmp_path / next(f for f in result["files"] if f.startswith("raw/web/"))
    note_path = tmp_path / next(f for f in result["files"] if f.startswith("wiki/articles/sources/"))
    assert "正文讲第二大脑" in raw_path.read_text(encoding="utf-8")
    note = note_path.read_text(encoding="utf-8")
    assert "extraction_status: complete" in note
    assert "web_extract" in note
    assert "## Actionable Insights for Ezra" in note
    assert "reply_text" in result
    assert "完整写入" in result["reply_text"]


def test_ingest_url_complete_runs_topic_enrichment(tmp_path: Path, monkeypatch) -> None:
    ingest = load_ingest()
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_for_topic_enrichment_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)

    html = """
    <html><body><article><h1>中小品牌做抖音人设IP</h1>
    <p>观点很简单：中小品牌做抖音，人设IP是杀出重围的终极武器。</p>
    <p>直播间要用千川投流和自然流内容配合，按选人、测试、放大推进。</p>
    </article></body></html>
    """

    result = ingest.ingest_url("https://example.com/douyin-persona", data_root=tmp_path, fetcher=lambda url: html)

    assert result["ok"] is True
    assert "topic_enrichment" in result
    assert result["topic_enrichment"]["ok"] is True
    topic_names = {t["name"] for t in result["topic_enrichment"]["topics"]}
    assert {"抖音电商", "人设 IP", "中小品牌起盘", "直播间投流复盘"}.issubset(topic_names)
    assert (tmp_path / "wiki" / "topics" / "persona-ip.md").exists()
    assert "topic_enrichment" in result["reply_text"] or "主题" in result["reply_text"]


def test_ingest_url_fetch_failure_falls_back_to_partial_router(tmp_path: Path, monkeypatch) -> None:
    ingest = load_ingest()
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_for_failure_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)

    def failing_fetcher(url: str) -> str:
        raise RuntimeError("blocked")

    result = ingest.ingest_url("https://example.com/blocked", data_root=tmp_path, fetcher=failing_fetcher)

    assert result["ok"] is True
    assert result["extraction_status"] == "partial"
    assert result["extraction_method"] == "manual_placeholder"
    assert "blocked" in result.get("extraction_error", "")
    assert "部分入库" in result["reply_text"] or "未完整解析" in result["reply_text"]


def test_article_url_ingest_cli_accepts_data_dir_and_prints_json(tmp_path: Path) -> None:
    html_file = tmp_path / "page.html"
    html_file.write_text(
        "<html><body><article><h1>CLI URL 抓取测试</h1><p>正文讲第二大脑。</p><p>正文讲直播间复盘。</p></article></body></html>",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(INGEST),
            "--url",
            html_file.as_uri(),
            "--data-dir",
            str(tmp_path / "brain"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    data = json.loads(completed.stdout)
    assert data["ok"] is True
    assert data["extraction_status"] == "complete"
    assert data["title"] == "CLI URL 抓取测试"
    assert "reply_text" in data
