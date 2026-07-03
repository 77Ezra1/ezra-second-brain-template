#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_EXTRACT = ROOT / "scripts" / "document_extract.py"
BUILDER = ROOT / "scripts" / "article_payload_builder.py"
BRAIN_CLI = ROOT / "scripts" / "brain_cli.py"
ROUTER = ROOT / "scripts" / "telegram_brain_router.py"
ARTICLE_TOPIC_ENRICHER = ROOT / "scripts" / "article_topic_enricher.py"


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_brain_cli():
    return load_module(BRAIN_CLI, "brain_cli_for_document_ingest")


def extract_document(
    path: Path,
    output: Path | None = None,
    preferred: list[str] | None = None,
    ocr_images: bool = False,
    ocr_max_pages: int = 20,
) -> dict[str, Any]:
    mod = load_module(DOCUMENT_EXTRACT, "document_extract_for_ingest")
    return mod.extract_document(path, output=output, preferred=preferred, ocr_images=ocr_images, ocr_max_pages=ocr_max_pages)


def enrich_created_article(data_root: Path, result: dict[str, Any]) -> dict[str, Any] | None:
    article_files = [f for f in result.get("files", []) if str(f).startswith("wiki/articles/sources/")]
    if not article_files:
        return None
    enricher = load_module(ARTICLE_TOPIC_ENRICHER, "article_topic_enricher_for_document_ingest")
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


def ingest_document(
    path: str | Path,
    *,
    data_root: Path | None = None,
    focus: str = "",
    preferred: list[str] | None = None,
    ocr_images: bool = False,
    ocr_max_pages: int = 20,
) -> dict[str, Any]:
    data_root = Path(data_root).resolve() if data_root else ROOT
    src = Path(path).expanduser().resolve()
    extracted_path = Path(tempfile.gettempdir()) / f"hermes-document-ingest-{src.stem}.md"
    extraction = extract_document(src, output=extracted_path, preferred=preferred, ocr_images=ocr_images, ocr_max_pages=ocr_max_pages)
    if not extraction.get("ok"):
        title = src.stem or "document"
        brain = load_brain_cli()
        old_root = getattr(brain, "ROOT", ROOT)
        brain.ROOT = data_root
        payload = {
            "schema_version": "article-payload-v2",
            "url": src.as_uri() if src.exists() else str(src),
            "title": title,
            "source": "document_extract",
            "content": None,
            "extraction_status": "partial",
            "extraction_method": "document_failed",
            "extraction_notes": extraction.get("error", "document extraction failed"),
        }
        result = brain.create_article(payload["url"], payload=payload)
        brain.ROOT = old_root
        formatter = load_module(ROUTER, "router_formatter_for_document_ingest_partial")
        result["reply_text"] = formatter.format_article(result)
        result["extraction_error"] = extraction.get("error")
        result["document_extraction"] = extraction
        return result

    content = Path(extraction["content_file"]).read_text(encoding="utf-8")
    builder = load_module(BUILDER, "article_payload_builder_for_document_ingest")
    payload = builder.build_payload(
        url=src.as_uri(),
        title=extraction.get("title") or src.stem,
        content=content,
        source="document_extract",
        method=extraction.get("method") or "document_extract",
        status="complete",
        focus=focus,
    )
    payload["extraction_notes"] = "Document extracted via V2 chain: " + ", ".join(a.get("method", "") + ("✓" if a.get("ok") else "✗") for a in extraction.get("attempts", []))
    brain = load_brain_cli()
    old_root = getattr(brain, "ROOT", ROOT)
    brain.ROOT = data_root
    result = brain.create_article(payload["url"], payload=payload)
    brain.ROOT = old_root
    result["document_extraction"] = extraction
    enrichment = enrich_created_article(data_root, result)
    if enrichment:
        result["topic_enrichment"] = enrichment
        changed = result.setdefault("files", [])
        for p in enrichment.get("changed", []):
            if p not in changed:
                changed.append(p)
    formatter = load_module(ROUTER, "router_formatter_for_document_ingest")
    result["reply_text"] = append_topic_reply(formatter.format_article(result), enrichment)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a local document into the second brain as an article note.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--focus", default="")
    parser.add_argument("--preferred")
    parser.add_argument("--ocr-images", action="store_true", help="OCR embedded PDF images and append recognized text")
    parser.add_argument("--ocr-max-pages", type=int, default=20, help="Max PDF pages to scan for image OCR")
    args = parser.parse_args(argv)
    preferred = [p.strip() for p in args.preferred.split(",") if p.strip()] if args.preferred else None
    result = ingest_document(
        args.file,
        data_root=Path(args.data_dir) if args.data_dir else None,
        focus=args.focus,
        preferred=preferred,
        ocr_images=args.ocr_images,
        ocr_max_pages=args.ocr_max_pages,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
