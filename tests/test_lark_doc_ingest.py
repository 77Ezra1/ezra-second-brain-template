from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts" / "lark_doc_ingest.py"
ROUTER = ROOT / "scripts" / "telegram_brain_router.py"


def load_module(path: Path, prefix: str):
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lark_doc_ingest_archives_images_and_manifest(tmp_path: Path, monkeypatch) -> None:
    ingest = load_module(INGEST, "lark_doc_ingest_test")
    brain = ingest.load_module(ingest.BRAIN_CLI, "brain_cli_lark_doc_test")
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    monkeypatch.setattr(ingest, "load_brain_cli", lambda: brain)

    content = (
        '<title>巨量云图极速版产品图谱</title>'
        '<h1>用 | 产品模块使用指导</h1>'
        '<h2>直播策略</h2>'
        '<p>直播诊断提供直播场景多角度评估、诊断、复盘优化能力。</p>'
        '<img name="image.png" alt="直播诊断页面截图，展示流量结构、转化效率和复盘指标" mime="image/png" src="tok_img_1"/>'
    )

    monkeypatch.setattr(
        ingest,
        "fetch_doc",
        lambda doc: {"ok": True, "data": {"document": {"document_id": "doxcn_test", "revision_id": 7, "content": content}}},
    )

    def fake_download(items, assets_dir, limit=None):
        assets_dir.mkdir(parents=True, exist_ok=True)
        img = assets_dir / "001-tok_img_1.png"
        img.write_bytes(b"png")
        items[0]["downloaded"] = True
        items[0]["file"] = str(img)

    monkeypatch.setattr(ingest, "download_media_assets", fake_download)

    result = ingest.ingest_lark_doc("https://bytedance.larkoffice.com/docx/doxcn_test", data_root=tmp_path)

    assert result["ok"] is True
    assert result["media_count"] == 1
    assert result["downloaded_media_count"] == 1
    manifest = tmp_path / result["media_manifest"]
    assert manifest.exists()
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["media"][0]["alt"].startswith("直播诊断页面截图")
    article_files = [f for f in result["files"] if f.startswith("wiki/articles/sources/")]
    assert article_files
    article = (tmp_path / article_files[0]).read_text(encoding="utf-8")
    assert "## Media Assets" in article
    assert "直播诊断页面截图" in article
    assert "Media Manifest" in article


def test_router_lark_doc_url_uses_lark_ingest(tmp_path: Path, monkeypatch) -> None:
    router = load_module(ROUTER, "router_lark_doc_test")

    class FakeIngest:
        @staticmethod
        def ingest_lark_doc(url, data_root=None):
            return {"ok": True, "title": "巨量云图", "url": url, "files": ["wiki/articles/sources/x.md"], "reply_text": "ok", "media_count": 1}

    monkeypatch.setattr(router, "load_lark_doc_ingest", lambda: FakeIngest)
    data = router.run_routed("外脑存文章：https://bytedance.larkoffice.com/docx/doxcn6eNiFGt2B17FbmoEpkJ5tb", source="pytest", data_dir=str(tmp_path))

    assert data["ok"] is True
    assert data["command"] == "article"
    assert data["media_count"] == 1
    assert data["reply_text"] == "ok"
