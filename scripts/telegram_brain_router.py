#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
BRAIN_CLI = ROOT / "scripts" / "brain_cli.py"
ARTICLE_URL_INGEST = ROOT / "scripts" / "article_url_ingest.py"
DOCUMENT_ARTICLE_INGEST = ROOT / "scripts" / "document_article_ingest.py"
LARK_DOC_INGEST = ROOT / "scripts" / "lark_doc_ingest.py"


class RoutedCommand(NamedTuple):
    command: str
    payload: str
    prefix: str


PREFIXES: list[tuple[str, str]] = [
    ("外脑存文章OCR：", "article_ocr"),
    ("外脑存文章OCR:", "article_ocr"),
    ("外脑存文章 OCR：", "article_ocr"),
    ("外脑存文章 OCR:", "article_ocr"),
    ("外脑存文章：", "article"),
    ("外脑存文章:", "article"),
    ("外脑修正：", "correction"),
    ("外脑修正:", "correction"),
    ("外脑总结：", "summary"),
    ("外脑总结:", "summary"),
    ("外脑提问：", "questions"),
    ("外脑提问:", "questions"),
    ("外脑待办：", "action_open"),
    ("外脑待办:", "action_open"),
    ("外脑完成：", "action_done"),
    ("外脑完成:", "action_done"),
    ("外脑取消：", "action_cancel"),
    ("外脑取消:", "action_cancel"),
    ("外脑？", "query"),
    ("外脑?", "query"),
    ("外脑：", "capture"),
    ("外脑:", "capture"),
]


def load_brain_cli():
    spec = importlib.util.spec_from_file_location("second_brain_v1_brain_cli", BRAIN_CLI)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load brain_cli.py from {BRAIN_CLI}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_article_url_ingest():
    spec = importlib.util.spec_from_file_location("second_brain_article_url_ingest", ARTICLE_URL_INGEST)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load article_url_ingest.py from {ARTICLE_URL_INGEST}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_document_article_ingest():
    spec = importlib.util.spec_from_file_location("second_brain_document_article_ingest", DOCUMENT_ARTICLE_INGEST)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load document_article_ingest.py from {DOCUMENT_ARTICLE_INGEST}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_lark_doc_ingest():
    spec = importlib.util.spec_from_file_location("second_brain_lark_doc_ingest", LARK_DOC_INGEST)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load lark_doc_ingest.py from {LARK_DOC_INGEST}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def route_command(text: str) -> RoutedCommand:
    stripped = text.strip()
    for prefix, command in PREFIXES:
        if stripped.startswith(prefix):
            return RoutedCommand(command=command, payload=stripped[len(prefix):].strip(), prefix=prefix)
    raise ValueError("NO_COMMAND_MATCH")


def bullet_files(files: list[str], max_items: int = 6) -> str:
    if not files:
        return ""
    lines = [f"- `{item}`" for item in files[:max_items]]
    if len(files) > max_items:
        lines.append(f"- …另有 {len(files) - max_items} 个文件")
    return "\n".join(lines)


def format_capture(data: dict[str, Any]) -> str:
    cats = " / ".join(data.get("categories", [])) or "未分类"
    files = data.get("files", [])
    parts = ["已写入外脑。", f"类型：{cats}"]
    if files:
        parts.extend(["", "文件：", bullet_files(files)])
    return "\n".join(parts).strip()


def format_query(data: dict[str, Any]) -> str:
    answer = data.get("answer") or "没有查询结果。"
    files = data.get("files", [])
    if files and "来源" not in answer:
        return f"{answer}\n\n来源：\n{bullet_files(files)}"
    return answer


def format_article(data: dict[str, Any]) -> str:
    title = data.get("title") or "Untitled"
    url = data.get("url") or ""
    status = data.get("extraction_status") or "unknown"
    method = data.get("extraction_method") or "unknown"
    if status == "complete":
        parts = [f"文章已完整写入外脑：{title}"]
    elif status == "partial":
        parts = [f"文章已部分入库：{title}", "说明：未完整解析正文；后续可用 Hermes 抓取正文或直接粘贴正文后重新入库。"]
    else:
        parts = [f"文章已写入外脑：{title}"]
    parts.append(f"状态：{status} via {method}")
    if data.get("word_count") is not None:
        parts.append(f"字数：{data.get('word_count')}")
    if url:
        parts.append(f"URL：{url}")
    if data.get("files"):
        parts.extend(["", "文件：", bullet_files(data["files"])])
    return "\n".join(parts).strip()


def format_summary(data: dict[str, Any]) -> str:
    answer = data.get("answer") or "总结已生成。"
    file = data.get("file")
    if file and file not in answer:
        answer += f"\n文件：`{file}`"
    return answer


def format_questions(data: dict[str, Any]) -> str:
    answer = data.get("answer") or "问题已生成。"
    if "## Questions" in answer:
        answer = "外脑给你的 3 个问题：\n" + answer.split("## Questions", 1)[1].strip()
    if data.get("file"):
        answer += f"\n\n文件：`{data['file']}`"
    return answer.strip()


def format_correction(data: dict[str, Any]) -> str:
    if data.get("ok") and data.get("status") == "corrected":
        return "\n".join([
            "已修正外脑记录。",
            "",
            f"修改：{data.get('old', '')} → {data.get('new', '')}",
            "",
            "文件：",
            bullet_files(data.get("files", [])),
        ]).strip()
    if data.get("status") == "ambiguous":
        return data.get("message") or "找到多条可能记录，需要你说得更具体一点。"
    return data.get("message") or "暂时无法自动修正这条记录。"


def now(brain) -> Any:
    return brain.now_dt()


def today(brain) -> str:
    return brain.today()


def iso_now(brain) -> str:
    return brain.iso_now()


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def ensure_action_files(root: Path, brain) -> tuple[Path, Path, Path]:
    actions_dir = root / "wiki" / "actions"
    actions_dir.mkdir(parents=True, exist_ok=True)
    open_path = actions_dir / "open.md"
    completed_path = actions_dir / "completed.md"
    cancelled_path = actions_dir / "cancelled.md"
    if not open_path.exists():
        open_path.write_text(action_file_header("open", brain), encoding="utf-8")
    if not completed_path.exists():
        completed_path.write_text(action_file_header("completed", brain), encoding="utf-8")
    if not cancelled_path.exists():
        cancelled_path.write_text(action_file_header("cancelled", brain), encoding="utf-8")
    return open_path, completed_path, cancelled_path


def action_file_header(kind: str, brain) -> str:
    title = {"open": "Open Actions", "completed": "Completed Actions", "cancelled": "Cancelled Actions"}[kind]
    return f"""---
id: actions-{kind}
created: {iso_now(brain)}
updated: {iso_now(brain)}
type: actions
category: actions
tags: [actions, {kind}]
source: system
confidence: high
privacy: private
related: []
---

# {title}

"""


def normalize_action_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^(今天|明天|后天)?\s*提醒我", "", text).strip()
    text = re.sub(r"^(今天|明天|后天)?\s*", "", text).strip()
    return text.strip(" ，。；;：:") or "未命名待办"


def due_from_text(text: str, brain) -> str | None:
    base = now(brain).date()
    if "后天" in text:
        return (base + timedelta(days=2)).isoformat()
    if "明天" in text:
        return (base + timedelta(days=1)).isoformat()
    if "今天" in text:
        return base.isoformat()
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d{1,2})[./月](\d{1,2})日?", text)
    if m:
        return f"{base.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def action_id(brain) -> str:
    return "A-" + now(brain).strftime("%Y%m%d-%H%M%S")


def parse_action_line(line: str) -> dict[str, str] | None:
    if not line.startswith("- ["):
        return None
    status_match = re.match(r"- \[[ x~-]\] \*\*(?P<id>[^*]+)\*\* — (?P<title>.*?)(?:（due: (?P<due>.*?)）)?(?:（(?P<tail>.*?)）)?$", line)
    if not status_match:
        return None
    return {k: v or "" for k, v in status_match.groupdict().items()}


def append_action(root: Path, payload: str, source: str, brain) -> dict[str, Any]:
    open_path, _, _ = ensure_action_files(root, brain)
    title = normalize_action_text(payload)
    due = due_from_text(payload, brain)
    aid = action_id(brain)
    due_part = f"（due: {due}）" if due else ""
    line = f"- [ ] **{aid}** — {title}{due_part}（source: {source}; created: {iso_now(brain)}）\n"
    with open_path.open("a", encoding="utf-8") as f:
        f.write(line)
    brain.append_log(f"action opened: {title}", [open_path])
    action = {"id": aid, "title": title, "due": due, "status": "open", "source": source}
    return {"ok": True, "command": "action_open", "action": action, "files": [rel(root, open_path)], "reply_text": f"已加入待办：{title}" + (f"\n到期：{due}" if due else "")}


def score_action(query: str, title: str) -> int:
    q = re.sub(r"\s+", "", query)
    t = re.sub(r"\s+", "", title)
    if not q or not t:
        return 0
    if q in t or t in q:
        return max(len(q), len(t))
    tokens = [part for part in re.split(r"[\s，。；;、]+", query) if part]
    score = sum(len(token) for token in tokens if token in title)
    for i in range(max(0, len(q) - 1)):
        if q[i:i+2] in t:
            score += 1
    return score


def transition_action(root: Path, payload: str, target_status: str, brain) -> dict[str, Any]:
    open_path, completed_path, cancelled_path = ensure_action_files(root, brain)
    lines = open_path.read_text(encoding="utf-8").splitlines(keepends=True)
    candidates: list[tuple[int, int, dict[str, str]]] = []
    for idx, line in enumerate(lines):
        parsed = parse_action_line(line.strip())
        if not parsed:
            continue
        score = score_action(payload, parsed["title"])
        if score > 0:
            candidates.append((score, idx, parsed))
    if not candidates:
        return {"ok": False, "command": f"action_{target_status}", "error_code": "ACTION_NOT_FOUND", "reply_text": "没有找到匹配的未闭环待办。"}
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return {"ok": False, "command": f"action_{target_status}", "error_code": "ACTION_AMBIGUOUS", "reply_text": "找到多条可能待办，需要你说得更具体一点。"}
    _, idx, parsed = candidates[0]
    original = lines.pop(idx).strip()
    open_path.write_text("".join(lines), encoding="utf-8")
    dest = completed_path if target_status == "done" else cancelled_path
    checkbox = "x" if target_status == "done" else "-"
    verb = "completed" if target_status == "done" else "cancelled"
    line = re.sub(r"^- \[[^\]]\]", f"- [{checkbox}]", original)
    line += f"（{verb}: {iso_now(brain)}）\n"
    with dest.open("a", encoding="utf-8") as f:
        f.write(line)
    brain.append_log(f"action {verb}: {parsed['title']}", [open_path, dest])
    action = {"id": parsed["id"], "title": parsed["title"], "due": parsed.get("due") or None, "status": target_status}
    reply_prefix = "已完成" if target_status == "done" else "已取消"
    return {"ok": True, "command": f"action_{target_status}", "action": action, "files": [rel(root, open_path), rel(root, dest)], "reply_text": f"{reply_prefix}：{parsed['title']}"}


def parse_pasted_article_payload(payload: str, source: str) -> dict[str, Any] | None:
    if "正文：" not in payload and "正文:" not in payload:
        return None
    title_match = re.search(r"标题[：:]\s*(.+)", payload)
    body_match = re.search(r"正文[：:]\s*(.+)", payload, re.S)
    title = title_match.group(1).strip() if title_match else "pasted-article"
    body = body_match.group(1).strip() if body_match else ""
    if not body:
        return None
    return {
        "schema_version": "article-payload-v2",
        "url": f"pasted://{title}",
        "title": title,
        "source": source,
        "content": body,
        "extraction_status": "complete",
        "extraction_method": "pasted_text",
    }


def url_only_article_payload(payload: str, source: str) -> dict[str, Any]:
    first_line = payload.strip().splitlines()[0] if payload.strip() else "article"
    url_match = re.search(r"(?:https?|file)://\S+", payload)
    url = url_match.group(0) if url_match else first_line
    title = url.rstrip("/").split("/")[-1] or url
    return {
        "schema_version": "article-payload-v2",
        "url": url,
        "title": title,
        "source": source,
        "content": None,
        "extraction_status": "partial",
        "extraction_method": "manual_placeholder",
        "extraction_notes": "Router received a URL/text pointer but no extracted article body. Use Hermes web extraction or paste full text for complete ingestion.",
    }


def article_url_from_payload(payload: str) -> str | None:
    m = re.search(r"(?:https?|file)://\S+", payload.strip())
    return m.group(0) if m else None


def is_lark_doc_url(url: str) -> bool:
    lowered = url.lower()
    return ("/docx/" in lowered or "/wiki/" in lowered) and any(host in lowered for host in ["larkoffice.com", "feishu.cn", "doubao.com"])


def document_ocr_options_from_payload(payload: str, *, force_ocr: bool = False) -> tuple[str, bool, int]:
    cleaned = payload.strip()
    ocr_images = force_ocr or bool(re.search(r"(?:^|\s)--ocr(?:-images)?(?:\s|$)", cleaned, re.I))
    max_pages = 20

    page_match = re.search(r"(?:^|\s)--ocr-(?:max-)?pages[=\s]+(\d+)(?:\s|$)", cleaned, re.I)
    if not page_match:
        page_match = re.search(r"(?:OCR\s*)?前\s*(\d+)\s*页", cleaned, re.I)
    if page_match:
        max_pages = max(1, int(page_match.group(1)))

    cleaned = re.sub(r"(?:^|\s)--ocr(?:-images)?(?:\s|$)", " ", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"(?:^|\s)--ocr-(?:max-)?pages(?:=|\s+)\d+(?:\s|$)", " ", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"(?:OCR\s*)?前\s*\d+\s*页", " ", cleaned, flags=re.I).strip()
    return cleaned, ocr_images, max_pages


def local_document_from_payload(payload: str) -> Path | None:
    candidate = payload.strip().strip('"').strip("'")
    if not candidate or re.match(r"^[a-z]+://", candidate, re.I):
        return None
    path = Path(candidate).expanduser()
    if path.exists() and path.is_file():
        suffix = path.suffix.lower()
        if suffix in {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".epub", ".md", ".txt", ".markdown"}:
            return path
    return None


def run_routed(text: str, source: str = "telegram", data_dir: str | None = None) -> dict[str, Any]:
    root = Path(data_dir).resolve() if data_dir else ROOT
    try:
        routed = route_command(text)
    except ValueError:
        return {
            "ok": False,
            "error_code": "NO_COMMAND_MATCH",
            "reply_text": "我没识别出外脑命令。可用：外脑：/外脑？/外脑修正：/外脑总结：/外脑存文章：/外脑待办：/外脑完成：/外脑取消：",
        }

    brain = load_brain_cli()
    brain.ROOT = root
    payload = routed.payload

    if routed.command == "capture":
        data = brain.capture(payload, source)
        data["reply_text"] = format_capture(data)
    elif routed.command == "query":
        data = brain.query_notes(payload)
        data["reply_text"] = format_query(data)
    elif routed.command == "correction":
        data = brain.correct(payload)
        data["reply_text"] = format_correction(data)
    elif routed.command == "summary":
        data = brain.summarize(payload)
        data["reply_text"] = format_summary(data)
    elif routed.command == "questions":
        data = brain.questions(payload)
        data["reply_text"] = format_questions(data)
    elif routed.command in {"article", "article_ocr"}:
        document_payload, ocr_images, ocr_max_pages = document_ocr_options_from_payload(payload, force_ocr=routed.command == "article_ocr")
        pasted_payload = parse_pasted_article_payload(payload, source)
        if pasted_payload:
            data = brain.create_article(pasted_payload.get("url", ""), title=None, content=None, source=source, payload=pasted_payload)
            data["reply_text"] = format_article(data)
        else:
            article_url = article_url_from_payload(document_payload)
            if article_url:
                if is_lark_doc_url(article_url):
                    ingest = load_lark_doc_ingest()
                    data = ingest.ingest_lark_doc(article_url, data_root=root)
                else:
                    ingest = load_article_url_ingest()
                    data = ingest.ingest_url(article_url, data_root=root)
            else:
                document_path = local_document_from_payload(document_payload)
                if document_path:
                    ingest = load_document_article_ingest()
                    data = ingest.ingest_document(document_path, data_root=root, ocr_images=ocr_images, ocr_max_pages=ocr_max_pages)
                else:
                    article_payload = url_only_article_payload(document_payload or payload, source)
                    data = brain.create_article(article_payload.get("url", ""), title=None, content=None, source=source, payload=article_payload)
                    data["reply_text"] = format_article(data)
    elif routed.command == "action_open":
        data = append_action(root, payload, source, brain)
    elif routed.command == "action_done":
        data = transition_action(root, payload, "done", brain)
    elif routed.command == "action_cancel":
        data = transition_action(root, payload, "cancelled", brain)
    else:
        data = {"ok": False, "error_code": "UNSUPPORTED_COMMAND", "reply_text": "暂不支持这个外脑命令。"}

    data.setdefault("ok", True)
    data["command"] = routed.command
    data["payload"] = payload
    data["source"] = source
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route Telegram 外脑 commands to the local second-brain workflows.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--source", default="telegram")
    parser.add_argument("--data-dir", help="Override second-brain root; used by tests to avoid real data pollution.")
    args = parser.parse_args(argv)
    result = run_routed(args.text, args.source, args.data_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
