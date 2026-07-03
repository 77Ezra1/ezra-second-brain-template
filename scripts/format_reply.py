#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def load_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("No JSON provided on stdin")
    # Allow command transcripts that contain text before JSON.
    start = raw.find("{")
    if start == -1:
        raise SystemExit("No JSON object found on stdin")
    return json.loads(raw[start:])


def bullet_files(files: list[str], max_items: int = 6) -> str:
    if not files:
        return ""
    shown = files[:max_items]
    lines = [f"- `{f}`" for f in shown]
    if len(files) > max_items:
        lines.append(f"- …另有 {len(files) - max_items} 个文件")
    return "\n".join(lines)


def format_capture(data: dict[str, Any]) -> str:
    cats = " / ".join(data.get("categories", [])) or "未分类"
    files = data.get("files", [])
    return "\n".join([
        "已写入外脑。",
        f"类型：{cats}",
        "",
        "文件：",
        bullet_files(files),
    ]).strip()


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
    files = data.get("files", [])
    if status == "complete":
        parts = [f"文章已完整写入外脑：{title}"]
    elif status == "partial":
        parts = [
            f"文章已部分入库：{title}",
            "说明：未完整解析正文；后续可用 Hermes 抓取正文或直接粘贴正文后重新入库。",
        ]
    else:
        parts = [f"文章已写入外脑：{title}"]
    parts.append(f"状态：{status} via {method}")
    if data.get("word_count") is not None:
        parts.append(f"字数：{data.get('word_count')}")
    if url:
        parts.append(f"URL：{url}")
    if files:
        parts.extend(["", "文件：", bullet_files(files)])
    return "\n".join(parts).strip()


def format_summary(data: dict[str, Any]) -> str:
    answer = data.get("answer") or "总结已生成。"
    file = data.get("file")
    if file and file not in answer:
        answer += f"\n文件：`{file}`"
    return answer


def format_questions(data: dict[str, Any]) -> str:
    answer = data.get("answer") or "问题已生成。"
    file = data.get("file")
    # For Telegram, keep the useful Questions section and avoid dumping huge Basis.
    if "## Questions" in answer:
        answer = answer.split("## Questions", 1)[1].strip()
        answer = "外脑给你的 3 个问题：\n" + answer
    if file:
        answer += f"\n\n文件：`{file}`"
    return answer.strip()


def format_correction(data: dict[str, Any]) -> str:
    status = data.get("status")
    if data.get("ok") and status == "corrected":
        old = data.get("old", "")
        new = data.get("new", "")
        files = data.get("files", [])
        return "\n".join([
            "已修正外脑记录。",
            "",
            f"修改：{old} → {new}",
            "",
            "文件：",
            bullet_files(files),
        ]).strip()
    if status == "ambiguous":
        candidates = data.get("candidates", [])
        lines = ["找到多条可能记录，需要你说得更具体一点。"]
        if candidates:
            lines.append("")
            lines.append("候选：")
            for item in candidates[:6]:
                if isinstance(item, dict):
                    lines.append(f"- `{item.get('file', '')}`：{item.get('line', '')}")
                else:
                    lines.append(f"- `{item}`")
        return "\n".join(lines).strip()
    if status == "not_found":
        return data.get("message") or "没有找到可修正的匹配记录。"
    return data.get("message") or "暂时无法自动修正这条记录。"


def format_generic(data: dict[str, Any]) -> str:
    if "answer" in data:
        return str(data["answer"])
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Format second-brain CLI JSON for Telegram/Hermes replies")
    parser.add_argument("kind", choices=["capture", "query", "article", "summary", "questions", "correction", "generic"])
    args = parser.parse_args(argv)
    data = load_json()
    if args.kind == "capture":
        out = format_capture(data)
    elif args.kind == "query":
        out = format_query(data)
    elif args.kind == "article":
        out = format_article(data)
    elif args.kind == "summary":
        out = format_summary(data)
    elif args.kind == "questions":
        out = format_questions(data)
    elif args.kind == "correction":
        out = format_correction(data)
    else:
        out = format_generic(data)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
