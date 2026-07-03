from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "scripts" / "document_extract.py"
INGEST = ROOT / "scripts" / "document_article_ingest.py"
ROUTER = ROOT / "scripts" / "telegram_brain_router.py"


def load_module(path: Path, prefix: str):
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_document_prefers_markitdown_and_writes_markdown(tmp_path: Path, monkeypatch) -> None:
    extractor = load_module(EXTRACT, "document_extract_test")
    source = tmp_path / "report.docx"
    source.write_text("placeholder", encoding="utf-8")
    output = tmp_path / "out.md"

    monkeypatch.setattr(extractor, "extract_with_markitdown", lambda path: "# 抖音文档\n\n中小品牌做抖音要做人设IP。")

    result = extractor.extract_document(source, output=output)

    assert result["ok"] is True
    assert result["method"] == "markitdown"
    assert result["content_file"] == str(output)
    assert "人设IP" in output.read_text(encoding="utf-8")
    assert result["word_count"] > 0


def test_extract_document_falls_back_from_markitdown_to_pymupdf_for_pdf(tmp_path: Path, monkeypatch) -> None:
    extractor = load_module(EXTRACT, "document_extract_test")
    source = tmp_path / "deck.pdf"
    source.write_bytes(b"%PDF fake")

    def fail_markitdown(path: Path) -> str:
        raise RuntimeError("markitdown failed")

    monkeypatch.setattr(extractor, "extract_with_markitdown", fail_markitdown)
    monkeypatch.setattr(extractor, "extract_with_docling", lambda path: (_ for _ in ()).throw(RuntimeError("docling failed")))
    monkeypatch.setattr(extractor, "extract_with_marker", lambda path: (_ for _ in ()).throw(RuntimeError("marker failed")))
    monkeypatch.setattr(extractor, "extract_with_pymupdf", lambda path: "# PDF标题\n\n直播间投流复盘内容。")

    result = extractor.extract_document(source)

    assert result["ok"] is True
    assert result["method"] == "pymupdf"
    assert "markitdown" in result["attempts"][0]["method"]
    assert Path(result["content_file"]).exists()


def test_extract_document_appends_pdf_image_ocr_when_enabled(tmp_path: Path, monkeypatch) -> None:
    extractor = load_module(EXTRACT, "document_extract_test")
    source = tmp_path / "image-text.pdf"
    source.write_bytes(b"%PDF fake")
    output = tmp_path / "ocr.md"

    monkeypatch.setattr(extractor, "extract_with_markitdown", lambda path: "# 图片 PDF\n\n正文文本层。")
    monkeypatch.setattr(extractor, "ocr_pdf_images", lambda path, max_pages=20: [{"page": 1, "text": "图片里的文字：扫码关注直播间", "image_count": 1}])

    result = extractor.extract_document(source, output=output, ocr_images=True)

    assert result["ok"] is True
    assert result["image_ocr"]["pages"] == 1
    content = output.read_text(encoding="utf-8")
    assert "## Image OCR" in content
    assert "图片里的文字：扫码关注直播间" in content


def test_document_article_ingest_writes_article_and_enriches_topics(tmp_path: Path, monkeypatch) -> None:
    ingest = load_module(INGEST, "document_article_ingest_test")
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_for_document_ingest_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)
    source = tmp_path / "douyin-persona.docx"
    source.write_text("fake", encoding="utf-8")

    def fake_extract(path: Path, output: Path | None = None, preferred: list[str] | None = None, ocr_images: bool = False, ocr_max_pages: int = 20) -> dict:
        out = output or tmp_path / "extracted.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# 中小品牌做抖音人设IP\n\n观点很简单：中小品牌做抖音，人设IP是杀出重围的终极武器。\n直播间要用千川投流和自然流内容配合，按选人、测试、放大推进。", encoding="utf-8")
        return {"ok": True, "path": str(path), "title": "中小品牌做抖音人设IP", "method": "markitdown", "content_file": str(out), "word_count": 88, "attempts": [{"method": "markitdown", "ok": True}]}

    monkeypatch.setattr(ingest, "extract_document", fake_extract)

    result = ingest.ingest_document(source, data_root=tmp_path)

    assert result["ok"] is True
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "markitdown"
    assert result["title"] == "中小品牌做抖音人设IP"
    assert "topic_enrichment" in result
    assert (tmp_path / "wiki" / "topics" / "persona-ip.md").exists()
    assert "主题：" in result["reply_text"]


def test_router_article_local_document_path_ingests_document(tmp_path: Path) -> None:
    doc = tmp_path / "local-doc.md"
    doc.write_text("# 本地抖音文档\n\n中小品牌做抖音，人设IP是核心。直播间用千川投流测试。", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(ROUTER), "--text", f"外脑存文章：{doc}", "--source", "pytest", "--data-dir", str(tmp_path / "brain")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(completed.stdout)

    assert data["ok"] is True
    assert data["command"] == "article"
    assert data["extraction_status"] == "complete"
    assert data["title"] == "本地抖音文档"
    assert "完整写入" in data["reply_text"]
