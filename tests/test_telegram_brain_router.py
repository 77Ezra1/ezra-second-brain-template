from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "telegram_brain_router.py"


def load_router():
    module_name = f"telegram_brain_router_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, ROUTER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_router(text: str, data_dir: Path, source: str = "pytest") -> dict:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--text",
            text,
            "--source",
            source,
            "--data-dir",
            str(data_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def test_route_command_recognizes_v2_prefixes() -> None:
    router = load_router()

    assert router.route_command("外脑：早餐 4 元").command == "capture"
    assert router.route_command("外脑？今天早餐花了多少").command == "query"
    assert router.route_command("外脑修正：早餐不是3元，是4元").command == "correction"
    assert router.route_command("外脑总结：本周").command == "summary"
    assert router.route_command("外脑提问：最近一个月").command == "questions"
    assert router.route_command("外脑存文章：https://example.com/a").command == "article"
    assert router.route_command("外脑存文章OCR：C:/tmp/a.pdf").command == "article_ocr"
    assert router.route_command("外脑存文章 OCR：C:/tmp/a.pdf").command == "article_ocr"
    assert router.route_command("外脑待办：明天提醒我问小王要排班表").command == "action_open"
    assert router.route_command("外脑完成：问小王要排班表").command == "action_done"
    assert router.route_command("外脑取消：问小王要排班表").command == "action_cancel"


def test_router_capture_returns_reply_text_and_preserves_test_isolation(tmp_path: Path) -> None:
    result = run_router("外脑：早餐 4 元", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "capture"
    assert "reply_text" in result
    assert "已写入外脑" in result["reply_text"]
    assert result["test_source"] is True
    assert list((tmp_path / "raw" / "pytest").glob("*.jsonl"))
    assert not (tmp_path / "wiki" / "finance" / "expenses").exists()


def test_router_query_formats_cli_answer(tmp_path: Path) -> None:
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / "2026-06.md"
    expense_file.parent.mkdir(parents=True)
    expense_file.write_text(
        "| Date | Item | Amount | Category | Notes | Source |\n"
        "|---|---:|---:|---|---|---|\n"
        "| 2026-06-27 | 真实早餐 | 8 | food |  | telegram |\n",
        encoding="utf-8",
    )

    result = run_router("外脑？2026-06 早餐花了多少", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "query"
    assert "2026-06 已记录真实消费合计 8 元" in result["reply_text"]
    assert result["files"] == ["wiki/finance/expenses/2026-06.md"]


def test_router_query_uses_exact_topic_answer(tmp_path: Path) -> None:
    topic = tmp_path / "wiki" / "topics" / "persona-ip.md"
    topic.parent.mkdir(parents=True)
    topic.write_text(
        "# 人设 IP\n\n"
        "## Core Claims\n\n- 人设 IP 解决信任缺失。\n\n"
        "## Metrics\n\n- ROI\n- 自然流占比\n",
        encoding="utf-8",
    )

    result = run_router("外脑？人设IP 指标", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "query"
    assert result["type"] == "topic"
    assert "## 人设 IP — Metrics" in result["reply_text"]
    assert "自然流占比" in result["reply_text"]
    assert result["files"] == ["wiki/topics/persona-ip.md"]


def test_router_query_time_and_source_type_precise_articles(tmp_path: Path) -> None:
    article = tmp_path / "wiki" / "articles" / "sources" / "2026-06-28-persona.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\ncreated: 2026-06-28T10:00:00+08:00\nurl: https://example.com/persona\n---\n\n"
        "# 人设IP来源文章\n\n"
        "## Executive Summary\n\n- 人设IP 来源文章摘要。\n\n"
        "## Actionable Insights for Ezra\n\n- 选主播时看可信标签。\n",
        encoding="utf-8",
    )

    result = run_router("外脑？2026-06 人设IP 行动建议", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "query"
    assert result["type"] == "precise_source"
    assert result["source_type"] == "action_insights"
    assert result["time_filter"] == {"kind": "month", "month": "2026-06"}
    assert "选主播时看可信标签" in result["reply_text"]
    assert "来源：" in result["reply_text"]
    assert result["files"] == ["wiki/articles/sources/2026-06-28-persona.md"]


def test_router_action_open_done_cancel_updates_action_files(tmp_path: Path) -> None:
    opened = run_router("外脑待办：明天提醒我问小王要 3 号直播间排班表", tmp_path)

    assert opened["ok"] is True
    assert opened["command"] == "action_open"
    assert opened["action"]["status"] == "open"
    assert opened["action"]["due"] is not None
    assert "已加入待办" in opened["reply_text"]
    open_file = tmp_path / "wiki" / "actions" / "open.md"
    assert "问小王要 3 号直播间排班表" in open_file.read_text(encoding="utf-8")

    done = run_router("外脑完成：问小王要排班表", tmp_path)

    assert done["ok"] is True
    assert done["command"] == "action_done"
    assert done["action"]["status"] == "done"
    assert "已完成" in done["reply_text"]
    completed_file = tmp_path / "wiki" / "actions" / "completed.md"
    assert "问小王要 3 号直播间排班表" in completed_file.read_text(encoding="utf-8")
    assert "问小王要 3 号直播间排班表" not in open_file.read_text(encoding="utf-8")

    opened_again = run_router("外脑待办：今天提醒我检查千川投流数据", tmp_path)
    assert opened_again["ok"] is True
    cancelled = run_router("外脑取消：检查千川投流数据", tmp_path)

    assert cancelled["ok"] is True
    assert cancelled["command"] == "action_cancel"
    assert cancelled["action"]["status"] == "cancelled"
    assert "已取消" in cancelled["reply_text"]


def test_router_article_pasted_text_creates_complete_article(tmp_path: Path) -> None:
    result = run_router("外脑存文章：\n标题：直播间转化率优化方法\n正文：\n第一段。\n第二段讲转化率。", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "article"
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "pasted_text"
    assert "完整写入" in result["reply_text"]
    note_path = tmp_path / next(f for f in result["files"] if f.startswith("wiki/articles/sources/"))
    assert "第二段讲转化率" in note_path.read_text(encoding="utf-8")


def test_router_article_url_auto_ingests_file_url_as_complete(tmp_path: Path) -> None:
    html_file = tmp_path / "article.html"
    html_file.write_text(
        "<html><body><article><h1>Router URL 自动抓取测试</h1><p>正文讲第二大脑。</p><p>正文讲直播间复盘。</p></article></body></html>",
        encoding="utf-8",
    )

    result = run_router(f"外脑存文章：{html_file.as_uri()}", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "article"
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "web_extract"
    assert result["title"] == "Router URL 自动抓取测试"
    assert "完整写入" in result["reply_text"]
    note_path = tmp_path / next(f for f in result["files"] if f.startswith("wiki/articles/sources/"))
    assert "正文讲直播间复盘" in note_path.read_text(encoding="utf-8")


def test_router_article_url_fetch_failure_is_partial_not_fake_complete(tmp_path: Path) -> None:
    result = run_router("外脑存文章：file:///C:/definitely/missing/router-article.html", tmp_path)

    assert result["ok"] is True
    assert result["command"] == "article"
    assert result["extraction_status"] == "partial"
    assert result["extraction_method"] == "manual_placeholder"
    assert "extraction_error" in result
    assert "部分入库" in result["reply_text"] or "未完整解析" in result["reply_text"]


def test_router_article_ocr_prefix_passes_document_ocr_options(tmp_path: Path, monkeypatch) -> None:
    router = load_router()
    doc = tmp_path / "scan.pdf"
    doc.write_bytes(b"%PDF fake")
    calls: list[dict] = []

    class FakeBrain:
        ROOT = tmp_path

    class FakeDocumentIngest:
        @staticmethod
        def ingest_document(path: Path, *, data_root: Path | None = None, ocr_images: bool = False, ocr_max_pages: int = 20, **kwargs) -> dict:
            calls.append({"path": path, "data_root": data_root, "ocr_images": ocr_images, "ocr_max_pages": ocr_max_pages})
            return {"ok": True, "extraction_status": "complete", "extraction_method": "pymupdf", "title": "scan", "files": [], "reply_text": "ok"}

    monkeypatch.setattr(router, "load_brain_cli", lambda: FakeBrain())
    monkeypatch.setattr(router, "load_document_article_ingest", lambda: FakeDocumentIngest)

    result = router.run_routed(f"外脑存文章OCR：{doc} --ocr-max-pages 7", source="pytest", data_dir=str(tmp_path / "brain"))

    assert result["ok"] is True
    assert result["command"] == "article_ocr"
    assert calls == [{"path": doc, "data_root": tmp_path / "brain", "ocr_images": True, "ocr_max_pages": 7}]


def test_router_article_inline_ocr_flag_passes_document_ocr_options(tmp_path: Path, monkeypatch) -> None:
    router = load_router()
    doc = tmp_path / "scan.pdf"
    doc.write_bytes(b"%PDF fake")
    calls: list[dict] = []

    class FakeBrain:
        ROOT = tmp_path

    class FakeDocumentIngest:
        @staticmethod
        def ingest_document(path: Path, *, data_root: Path | None = None, ocr_images: bool = False, ocr_max_pages: int = 20, **kwargs) -> dict:
            calls.append({"path": path, "data_root": data_root, "ocr_images": ocr_images, "ocr_max_pages": ocr_max_pages})
            return {"ok": True, "extraction_status": "complete", "extraction_method": "pymupdf", "title": "scan", "files": [], "reply_text": "ok"}

    monkeypatch.setattr(router, "load_brain_cli", lambda: FakeBrain())
    monkeypatch.setattr(router, "load_document_article_ingest", lambda: FakeDocumentIngest)

    result = router.run_routed(f"外脑存文章：{doc} --ocr-images OCR前3页", source="pytest", data_dir=str(tmp_path / "brain"))

    assert result["ok"] is True
    assert result["command"] == "article"
    assert calls == [{"path": doc, "data_root": tmp_path / "brain", "ocr_images": True, "ocr_max_pages": 3}]


def test_router_unknown_command_returns_clear_error(tmp_path: Path) -> None:
    result = run_router("外脑帮我随便处理一下", tmp_path)

    assert result["ok"] is False
    assert result["error_code"] == "NO_COMMAND_MATCH"
    assert "可用" in result["reply_text"]
