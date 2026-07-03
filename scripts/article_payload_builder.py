#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text)) + len(re.findall(r"[A-Za-z0-9_]+", text))


def first_heading(content: str) -> str | None:
    for line in content.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def extract_author(content: str) -> str:
    patterns = [r"(?:作者|Author)[:：]\s*(.+)", r"(?:来源|Source)[:：]\s*(.+)"]
    for pattern in patterns:
        m = re.search(pattern, content, re.I)
        if m:
            return m.group(1).strip()
    return ""


def extract_published(content: str) -> str:
    patterns = [r"(?:发布时间|发布|Published|Date)[:：]\s*(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})", r"\b(20\d{2}-\d{1,2}-\d{1,2})\b"]
    for pattern in patterns:
        m = re.search(pattern, content, re.I)
        if m:
            return m.group(1).replace("/", "-").replace(".", "-")
    return ""


def extract_headings(content: str) -> list[str]:
    headings = []
    for line in content.splitlines():
        m = re.match(r"^#{2,4}\s+(.+?)\s*$", line.strip())
        if m:
            headings.append(m.group(1).strip())
    return headings


def sentences(content: str, limit: int = 6) -> list[str]:
    cleaned = re.sub(r"^#+\s+.*$", "", content, flags=re.M)
    parts = [p.strip() for p in re.split(r"(?<=[。！？.!?])\s+|\n+", cleaned) if p.strip()]
    return parts[:limit]


INTRO_PATTERNS = ["最近忙着", "没什么表达欲", "今天这篇文章", "看到一个案例", "祝福屏幕前", "希望我今天"]
CORE_KEYWORDS = ["观点", "核心", "底层逻辑", "痛点", "信任", "壁垒", "流量", "品牌资产", "起盘", "步骤", "选人", "测试", "放大", "人设", "创始人IP", "人设IP", "抖音", "直播间"]


def sentence_candidates(content: str) -> list[str]:
    cleaned = re.sub(r"^#+\s+.*$", "", content, flags=re.M)
    parts = [p.strip(" ；;。") for p in re.split(r"(?<=[。！？.!?])\s+|\n+", cleaned) if p.strip()]
    return [p for p in parts if len(p) >= 8 and not p.startswith("![图片]")]


def sentence_score(text: str) -> int:
    score = 0
    for bad in INTRO_PATTERNS:
        if bad in text:
            score -= 8
    for kw in CORE_KEYWORDS:
        if kw in text:
            score += 3
    if re.match(r"^\d+[、：:]", text):
        score += 5
    if "——" in text or "：" in text or ":" in text:
        score += 2
    if re.search(r"\d|GMV|ROI|TOP", text, re.I):
        score += 1
    if len(text) > 120:
        score -= 1
    return score


def core_sentences(content: str, limit: int = 6) -> list[str]:
    candidates = sentence_candidates(content)
    if not candidates:
        return sentences(content, limit)
    ranked = sorted(enumerate(candidates), key=lambda item: (-sentence_score(item[1]), item[0]))
    chosen = [text for _, text in ranked if sentence_score(text) > 0][:limit]
    if len(chosen) < min(limit, 3):
        chosen.extend(text for _, text in ranked if text not in chosen)
    return chosen[:limit]


def infer_core_thesis(content: str, title: str, summary_items: list[str]) -> str:
    for candidate in sentence_candidates(content):
        if ("观点" in candidate or "标题想讲" in candidate) and ("人设" in candidate or "抖音" in candidate):
            return candidate
    for candidate in summary_items:
        if "中小品牌" in candidate and ("抖音" in candidate or "人设" in candidate):
            return candidate
    return summary_items[0] if summary_items else title


def infer_concepts(content: str, focus: str = "") -> list[str]:
    concepts: list[str] = []
    candidates = {
        "人设 IP": [["人设IP"], ["人设", "IP"], ["创始人IP"], ["创始人", "出镜"]],
        "抖音电商": [["抖音", "电商"], ["抖音", "直播间"], ["千川"]],
        "中小品牌起盘": [["中小品牌"], ["小品牌"], ["白牌"], ["起盘"]],
        "直播间投流复盘": [["投流", "直播间"], ["直播间", "复盘"], ["千川", "ROI"], ["自然流", "付费流量"]],
        "转化率": [["转化率"]],
        "GMV": [["GMV"], ["gmv"]],
        "主播状态": [["主播", "状态"]],
        "第二大脑": [["第二大脑"], ["外脑"]],
        "Wiki 沉淀": [["Wiki", "沉淀"]],
    }
    haystack = content + "\n" + focus
    for concept, alternatives in candidates.items():
        if any(all(k in haystack for k in keys) for keys in alternatives):
            concepts.append(concept)
    return concepts or extract_headings(content)[:5]


def actionable_insights(content: str, focus: str = "") -> list[str]:
    insights: list[str] = []
    haystack = content + "\n" + focus
    if "选人" in haystack and "测试" in haystack and "放大" in haystack:
        insights.append("把人设 IP 起盘拆成“选人-测试-放大”三步：先选懂产品且敢表达的人，再测内容框架/场景/形式，最后放大核心标签和信任背书。")
    if "直播间" in haystack or "投流" in haystack or "千川" in haystack:
        insights.append("结合直播间场次数据，把人设内容作为千川素材与自然流内容双线测试，并复盘 ROI、自然流占比和粉丝复看。")
    if "中小品牌" in haystack or "白牌" in haystack:
        insights.append("对中小品牌/白牌，不只比价格和参数，要用真人出镜把原料、工艺、品控和价值观可视化，先补信任缺口。")
    if "第二大脑" in haystack or "Wiki" in haystack or "外脑" in haystack:
        insights.append("把文章核心概念沉淀到 Wiki，并在后续复盘中反复链接使用。")
    if focus:
        insights.append(f"按用户关注点复读：{focus}")
    return insights or ["提取可执行步骤，并在相关项目页中建立链接。"]


def build_payload(
    *,
    url: str,
    title: str | None,
    content: str,
    source: str = "web_extract",
    method: str = "web_extract",
    status: str = "complete",
    focus: str = "",
) -> dict[str, Any]:
    actual_title = title or first_heading(content) or url.rstrip("/").split("/")[-1] or "article"
    summary_items = core_sentences(content, 6)
    headings = extract_headings(content)
    concepts = infer_concepts(content, focus)
    core_thesis = infer_core_thesis(content, actual_title, summary_items)
    return {
        "schema_version": "article-payload-v2",
        "url": url,
        "title": actual_title,
        "author": extract_author(content),
        "published": extract_published(content),
        "source": source,
        "content": content,
        "tl_dr": core_thesis,
        "summary": summary_items or [actual_title],
        "core_thesis": core_thesis,
        "structure": headings,
        "key_points": summary_items,
        "important_details": [s for s in summary_items if re.search(r"\d|GMV|转化|案例|数据|信任|流量|壁垒|品牌资产", s, re.I)],
        "concepts": concepts,
        "actionable_insights": actionable_insights(content, focus),
        "possible_applications": ["写入第二大脑 Wiki 后，用于后续查询、复盘和主题页沉淀。"],
        "critique": ["自动 payload builder 只做确定性初筛，深度判断需 Hermes/人工进一步补充。"],
        "quotes": summary_items[:2],
        "follow_up_questions": ["这篇文章最值得落地的一条行动是什么？", "它应该链接到哪个项目或工作主题页？"],
        "related": [],
        "extraction_status": status,
        "extraction_method": method,
        "extraction_notes": f"Payload built from extracted content. focus={focus}" if focus else "Payload built from extracted content.",
        "word_count": word_count(content),
        "content_hash": content_hash(content),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build article-payload-v2 JSON from extracted article/document text.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--title")
    parser.add_argument("--content-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source", default="web_extract")
    parser.add_argument("--method", default="web_extract")
    parser.add_argument("--status", default="complete", choices=["complete", "partial", "failed"])
    parser.add_argument("--focus", default="")
    args = parser.parse_args(argv)

    content = Path(args.content_file).read_text(encoding="utf-8")
    payload = build_payload(url=args.url, title=args.title, content=content, source=args.source, method=args.method, status=args.status, focus=args.focus)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "title": payload["title"], "word_count": payload["word_count"], "content_hash": payload["content_hash"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
