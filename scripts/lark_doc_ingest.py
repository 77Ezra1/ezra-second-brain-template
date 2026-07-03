#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "article_payload_builder.py"
BRAIN_CLI = ROOT / "scripts" / "brain_cli.py"
ROUTER = ROOT / "scripts" / "telegram_brain_router.py"
ARTICLE_TOPIC_ENRICHER = ROOT / "scripts" / "article_topic_enricher.py"
JULIANG_YUNTU_TOPIC_BUILDER = ROOT / "scripts" / "juliang_yuntu_topic_builder.py"


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_brain_cli():
    return load_module(BRAIN_CLI, "brain_cli_for_lark_doc_ingest")


def slugify(text: str, max_len: int = 60) -> str:
    text = text.strip().lower()
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = text.strip("-")
    return (text[:max_len].strip("-") or "lark-doc")


def lark_cli_executable() -> str:
    found = shutil.which("lark-cli")
    if found:
        return found
    candidates = [
        Path.home() / "AppData" / "Roaming" / "npm" / "lark-cli.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "lark-cli",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "lark-cli"


def run_lark_cli(args: list[str], *, cwd: Path | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("LARKSUITE_CLI_NO_UPDATE_NOTIFIER", "1")
    env.setdefault("LARKSUITE_CLI_NO_SKILLS_NOTIFIER", "1")
    return subprocess.run(
        [lark_cli_executable(), *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def fetch_doc(doc: str) -> dict[str, Any]:
    completed = run_lark_cli(["docs", "+fetch", "--doc", doc, "--format", "json"], timeout=240)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "lark-cli docs +fetch failed").strip())
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli docs +fetch returned non-JSON output: {completed.stdout[:500]}") from exc
    if not data.get("ok"):
        raise RuntimeError(json.dumps(data.get("error") or data, ensure_ascii=False))
    return data


ATTR_RE = re.compile(r"([\w:-]+)=\"(.*?)\"")


def parse_attrs(raw: str) -> dict[str, str]:
    return {k: html.unescape(v) for k, v in ATTR_RE.findall(raw)}


def extract_media(content: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for idx, match in enumerate(re.finditer(r"<(img|source|whiteboard)\b([^>]*)/?>", content), start=1):
        tag = match.group(1)
        attrs = parse_attrs(match.group(2))
        token = attrs.get("src") or attrs.get("token") or attrs.get("file-token") or ""
        alt = attrs.get("alt") or attrs.get("name") or ""
        item = {
            "index": idx,
            "type": "image" if tag == "img" else tag,
            "tag": tag,
            "token": token,
            "name": attrs.get("name") or f"{tag}-{idx}",
            "mime": attrs.get("mime") or "",
            "alt": alt,
            "scale": attrs.get("scale") or "",
            "downloaded": False,
            "file": "",
            "error": "",
        }
        items.append(item)
    return items


def download_media_assets(items: list[dict[str, Any]], assets_dir: Path, *, limit: int | None = None) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for item in items:
        token = item.get("token") or ""
        if not token:
            item["error"] = "missing token"
            continue
        if limit is not None and downloaded >= limit:
            item["error"] = "download skipped by limit"
            continue
        media_type = "whiteboard" if item.get("tag") == "whiteboard" else "media"
        safe_token = re.sub(r"[^A-Za-z0-9_.-]+", "_", token)[:80]
        output_stem = f"{int(item['index']):03d}-{safe_token}"
        commands = [["docs", "+media-download", "--type", media_type, "--token", token, "--output", f"./{output_stem}", "--overwrite", "--format", "json"]]
        if media_type == "media":
            commands.append(["docs", "+media-preview", "--token", token, "--output", f"./{output_stem}", "--overwrite", "--format", "json"])
        last_error = ""
        for command in commands:
            completed = run_lark_cli(command, cwd=assets_dir, timeout=180)
            if completed.returncode != 0:
                last_error = (completed.stderr or completed.stdout or "download failed").strip()[:500]
                continue
            try:
                data = json.loads(completed.stdout[completed.stdout.find("{"):])
            except Exception:
                last_error = f"download returned non-JSON: {completed.stdout[:200]}"
                continue
            if not data.get("ok"):
                last_error = json.dumps(data.get("error") or data, ensure_ascii=False)[:500]
                continue
            file_path = data.get("file_path") or data.get("path") or data.get("data", {}).get("saved_path") or ""
            item["downloaded"] = True
            item["file"] = str(file_path)
            item["error"] = ""
            downloaded += 1
            break
        if not item.get("downloaded"):
            item["error"] = last_error


def title_from_content(content: str, doc_id: str) -> str:
    patterns = [r"<title[^>]*>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>"]
    for pattern in patterns:
        m = re.search(pattern, content, flags=re.S)
        if m:
            title = strip_tags(m.group(1)).strip()
            if title:
                return title
    return doc_id or "飞书文档"


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def xml_to_markdown(content: str, media: list[dict[str, Any]], data_root: Path) -> str:
    media_by_token = {m.get("token"): m for m in media if m.get("token")}

    def image_repl(match: re.Match[str]) -> str:
        attrs = parse_attrs(match.group(2))
        token = attrs.get("src") or attrs.get("token") or ""
        item = media_by_token.get(token, {})
        alt = attrs.get("alt") or attrs.get("name") or item.get("alt") or "图片"
        file_path = item.get("file") or ""
        rel_file = ""
        if file_path:
            try:
                rel_file = str(Path(file_path).resolve().relative_to(data_root.resolve())).replace("\\", "/")
            except Exception:
                rel_file = file_path
        if rel_file:
            return f"\n\n![{alt}]({rel_file})\n\n"
        return f"\n\n[图片 {item.get('index', '')}: {alt}]\n\n"

    text = re.sub(r"<(img|source|whiteboard)\b([^>]*)/?>", image_repl, content)
    replacements = [
        (r"<title[^>]*>(.*?)</title>", r"# \1\n\n"),
        (r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n\n"),
        (r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n\n"),
        (r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n\n"),
        (r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n\n"),
        (r"</p>", "\n\n"),
        (r"<br\s*/?>", "\n"),
        (r"</li>", "\n"),
        (r"<li[^>]*>", "- "),
        (r"</tr>", "\n"),
        (r"</td>|</th>", " | "),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.S | re.I)
    text = strip_tags(text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    compact: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                compact.append("")
            blank = True
        else:
            compact.append(line)
            blank = False
    return "\n".join(compact).strip() + "\n"


def enrich_created_article(data_root: Path, result: dict[str, Any]) -> dict[str, Any] | None:
    article_files = [f for f in result.get("files", []) if str(f).startswith("wiki/articles/sources/")]
    if not article_files:
        return None
    enricher = load_module(ARTICLE_TOPIC_ENRICHER, "article_topic_enricher_for_lark_doc_ingest")
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
    return reply_text.rstrip() + "\n\n主题：" + "、".join(names) if names else reply_text


def build_juliang_yuntu_topics(data_root: Path, result: dict[str, Any]) -> dict[str, Any] | None:
    article_files = [f for f in result.get("files", []) if str(f).startswith("wiki/articles/sources/")]
    if not article_files:
        return None
    title = str(result.get("title") or "")
    url = str(result.get("url") or "")
    if "巨量云图" not in title and "yuntu" not in url.lower() and "bytedance.larkoffice.com" not in url.lower():
        return None
    builder = load_module(JULIANG_YUNTU_TOPIC_BUILDER, "juliang_yuntu_topic_builder_for_lark_doc_ingest")
    return builder.build_topics(data_root / article_files[0], data_root=data_root)


def ingest_lark_doc(
    doc: str,
    *,
    data_root: Path | None = None,
    focus: str = "",
    download_images: bool = True,
    image_limit: int | None = None,
) -> dict[str, Any]:
    data_root = Path(data_root).resolve() if data_root else ROOT
    fetched = fetch_doc(doc)
    document = fetched.get("data", {}).get("document", {})
    content = document.get("content") or ""
    doc_id = document.get("document_id") or doc.rstrip("/").split("/")[-1]
    revision_id = document.get("revision_id")
    title = title_from_content(content, doc_id)
    media = extract_media(content)
    slug = slugify(title)
    assets_dir = data_root / "raw" / "lark-doc-assets" / f"{doc_id}-{slug}"
    if download_images:
        download_media_assets(media, assets_dir, limit=image_limit)
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "url": doc,
        "document_id": doc_id,
        "revision_id": revision_id,
        "title": title,
        "media_count": len(media),
        "downloaded_count": sum(1 for item in media if item.get("downloaded")),
        "media": media,
    }
    (assets_dir / "media-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (assets_dir / "document.xml").write_text(content, encoding="utf-8")
    markdown = xml_to_markdown(content, media, data_root)
    media_summary = [
        f"图片{item['index']}: {item.get('alt') or item.get('name') or item.get('token')}" + (f"（文件：{item.get('file')}）" if item.get("downloaded") else "")
        for item in media
    ]
    if media_summary:
        markdown += "\n\n## Document Image Inventory\n\n" + "\n".join(f"- {line}" for line in media_summary) + "\n"

    builder = load_module(BUILDER, "article_payload_builder_for_lark_doc_ingest")
    payload = builder.build_payload(
        url=doc,
        title=title,
        content=markdown,
        source="lark_doc",
        method="lark-cli docs +fetch +media-download" if download_images else "lark-cli docs +fetch",
        status="complete",
        focus=focus,
    )
    payload["document_id"] = doc_id
    payload["revision_id"] = revision_id
    payload["media_assets"] = media
    payload["media_manifest"] = str((assets_dir / "media-manifest.json").relative_to(data_root)).replace("\\", "/")
    payload["raw_xml"] = str((assets_dir / "document.xml").relative_to(data_root)).replace("\\", "/")
    payload["extraction_notes"] = (
        f"Lark doc fetched via lark-cli. document_id={doc_id}; revision_id={revision_id}; "
        f"images={len(media)}; downloaded={sum(1 for item in media if item.get('downloaded'))}."
    )

    brain = load_brain_cli()
    old_root = getattr(brain, "ROOT", ROOT)
    brain.ROOT = data_root
    try:
        result = brain.create_article(doc, payload=payload)
    finally:
        brain.ROOT = old_root
    result["lark_document"] = {"document_id": doc_id, "revision_id": revision_id}
    result["media_count"] = len(media)
    result["downloaded_media_count"] = sum(1 for item in media if item.get("downloaded"))
    result["media_manifest"] = payload["media_manifest"]
    result["raw_xml"] = payload["raw_xml"]
    enrichment = enrich_created_article(data_root, result)
    if enrichment:
        result["topic_enrichment"] = enrichment
        changed = result.setdefault("files", [])
        for p in enrichment.get("changed", []):
            if p not in changed:
                changed.append(p)
    yuntu_topics = build_juliang_yuntu_topics(data_root, result)
    if yuntu_topics:
        result["juliang_yuntu_topics"] = yuntu_topics
        changed = result.setdefault("files", [])
        for p in yuntu_topics.get("changed", []):
            if p not in changed:
                changed.append(p)
    formatter = load_module(ROUTER, "router_formatter_for_lark_doc_ingest")
    result["reply_text"] = append_topic_reply(formatter.format_article(result), enrichment)
    result["reply_text"] += f"\n图片：{result['downloaded_media_count']}/{result['media_count']} 已归档"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a Lark/Feishu docx document into Ezra's second brain, including embedded images.")
    parser.add_argument("--doc", required=True, help="Lark/Feishu document URL or token")
    parser.add_argument("--data-dir")
    parser.add_argument("--focus", default="")
    parser.add_argument("--no-download-images", action="store_true")
    parser.add_argument("--image-limit", type=int)
    args = parser.parse_args(argv)
    result = ingest_lark_doc(
        args.doc,
        data_root=Path(args.data_dir) if args.data_dir else None,
        focus=args.focus,
        download_images=not args.no_download_images,
        image_limit=args.image_limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
