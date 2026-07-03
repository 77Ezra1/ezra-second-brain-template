#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOPIC_DIR = ROOT / "wiki" / "topics" / "巨量云图"

TOPICS = [
    {
        "name": "巨量云图/行业洞察",
        "slug": "industry-insight",
        "aliases": ["行业", "行业热榜", "行业热词", "行业达人", "行业内容", "竞争分析", "达人优选"],
        "keywords": ["行业热榜", "行业热词", "行业达人", "行业内容", "竞争分析", "达人优选", "热门视频", "热门商品", "相似抖音号", "相似直播间"],
        "scope": "用巨量云图极速版查看行业趋势、达人/内容/热词榜单、竞品账号与直播间表现。",
    },
    {
        "name": "巨量云图/人群分析",
        "slug": "audience-analysis",
        "aliases": ["人群", "我的人群", "行业人群", "自定义人群", "A4人群", "人群包"],
        "keywords": ["我的人群", "行业人群", "自定义人群", "A4人群", "破圈", "人群包", "直播人群", "高效成交属性"],
        "scope": "用巨量云图做人群资产、人群破圈、行业人群和直播人群转化分析。",
    },
    {
        "name": "巨量云图/商品策略",
        "slug": "product-strategy",
        "aliases": ["商品", "商品趋势策略", "单品策略", "货盘", "爆品", "卖点", "价格带"],
        "keywords": ["商品趋势策略", "单品策略", "货盘", "潜爆", "爆品", "卖点", "价格带", "品类趋势", "商品点击率", "点击成交率"],
        "scope": "用巨量云图做品类趋势、货盘诊断、单品潜力和直播货品复盘。",
    },
    {
        "name": "巨量云图/内容策略",
        "slug": "content-strategy",
        "aliases": ["内容", "行业内容", "我的内容", "抖音号分析", "自定义内容", "素材"],
        "keywords": ["行业内容", "我的内容", "抖音号分析", "自定义内容", "选题", "素材", "内容榜", "播放量", "互动率", "完播"],
        "scope": "用巨量云图分析内容选题、素材制作、抖音号内容质量和竞品内容差距。",
    },
    {
        "name": "巨量云图/直播策略",
        "slug": "live-strategy",
        "aliases": ["直播策略", "直播诊断", "直播人群", "直播排品", "开播策略", "引流策略", "直播复盘"],
        "keywords": ["直播诊断", "直播人群", "直播排品", "开播策略", "引流策略", "直播货品复盘", "流量结构", "转化效率", "场均GMV", "直播间", "开播时间"],
        "scope": "用巨量云图做直播诊断、直播人群、直播排品、开播策略、引流策略和场次复盘。",
    },
    {
        "name": "巨量云图/搜索策略",
        "slug": "search-strategy",
        "aliases": ["搜索", "搜索策略", "搜索词", "搜后看", "搜后购"],
        "keywords": ["搜索策略", "搜索词", "搜后看", "搜后购", "搜索人群", "热门搜索词"],
        "scope": "用巨量云图查看行业热门搜索词、搜索人群以及搜后看/搜后购内容。",
    },
    {
        "name": "巨量云图/投广策略",
        "slug": "ad-strategy",
        "aliases": ["投广", "投广指导", "投放", "千川", "计划创编", "创编参考", "人群圈选"],
        "keywords": ["投广指导", "投广诊断", "计划创编", "创编参考", "千川", "优化目标", "推广方式", "营销类型", "营销目标", "营销场景", "人群圈选", "消耗", "ROI"],
        "scope": "用巨量云图对比行业/竞对投放情况，辅助投放规划、计划基建、创编参考与人群圈选。",
    },
    {
        "name": "巨量云图/FAQ与后台流程",
        "slug": "faq-and-ops",
        "aliases": ["FAQ", "常见问题", "后台", "问题反馈", "消息中心", "官方社群"],
        "keywords": ["常见问题", "问题反馈流程", "消息中心", "官方飞书社群", "官网后台"],
        "scope": "巨量云图官网后台问题反馈、消息中心、官方社群和常见问题。",
    },
]


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + 4 :].lstrip()
    return text


def title_from_note(text: str, path: Path) -> str:
    m = re.search(r"^#\s+(.+)$", strip_frontmatter(text), re.M)
    return m.group(1).strip() if m else path.stem


def frontmatter_value(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def split_sections(markdown: str) -> list[dict[str, Any]]:
    body = strip_frontmatter(markdown)
    lines = body.splitlines()
    sections: list[dict[str, Any]] = []
    current = {"heading": "概览", "level": 1, "lines": []}
    for line in lines:
        m = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if m:
            if current["lines"]:
                sections.append(current)
            current = {"heading": m.group(2).strip(), "level": len(m.group(1)), "lines": [line]}
        else:
            current["lines"].append(line)
    if current["lines"]:
        sections.append(current)
    return sections


def score_topic(text: str, topic: dict[str, Any]) -> int:
    lowered = text.lower()
    score = 0
    for alias in topic["aliases"]:
        score += lowered.count(alias.lower()) * 4
    for keyword in topic["keywords"]:
        score += lowered.count(keyword.lower()) * 2
    if "巨量云图" in text:
        score += 1
    return score


def section_summary(text: str, max_len: int = 260) -> str:
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    cleaned = re.sub(r"[#>*_\-|]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len] + ("..." if len(cleaned) > max_len else "")


def image_lines(text: str, article_title: str, max_items: int = 12) -> list[str]:
    lines: list[str] = []
    for m in re.finditer(r"图片\s*(\d+)[:：]\s*(.*?)(?:（文件[:：](.*?)）)?(?:\n|$)", text):
        idx, alt, file = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        alt = alt[:220] + ("..." if len(alt) > 220 else "")
        suffix = f" — `{file}`" if file else ""
        lines.append(f"- 图片{idx}: {alt}（来源：{article_title}）{suffix}")
        if len(lines) >= max_items:
            break
    for m in re.finditer(r"!\[(.*?)\]\((.*?)\)", text):
        alt, file = m.group(1).strip(), m.group(2).strip()
        if not alt:
            continue
        alt = alt[:220] + ("..." if len(alt) > 220 else "")
        line = f"- {alt}（来源：{article_title}） — `{file}`"
        if line not in lines:
            lines.append(line)
        if len(lines) >= max_items:
            break
    return lines


def topic_path(topic: dict[str, Any], root: Path) -> Path:
    return root / "wiki" / "topics" / "巨量云图" / f"{topic['slug']}.md"


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def append_unique_section(text: str, heading: str, items: list[str]) -> tuple[str, bool]:
    items = [i for i in items if i.strip()]
    if not items:
        return text, False
    marker = f"## {heading}\n"
    if marker not in text:
        text += f"\n## {heading}\n\n"
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M)
    assert m
    start = m.end()
    nxt = re.search(r"^##\s+", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    current = text[start:end].strip()
    additions = [i for i in items if i not in current]
    if not additions:
        return text, False
    new_current = (current + "\n" if current else "") + "\n".join(additions) + "\n"
    return text[:start] + "\n" + new_current + text[end:], True


def ensure_topic(topic: dict[str, Any], root: Path) -> Path:
    path = topic_path(topic, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        aliases = "、".join(topic["aliases"])
        path.write_text(
            f"---\n"
            f"id: juliang-yuntu-{topic['slug']}\n"
            f"created: {now_iso()}\n"
            f"updated: {now_iso()}\n"
            f"type: topic\n"
            f"category: 巨量云图\n"
            f"tags: [topic, 巨量云图, 官方文档]\n"
            f"source: juliang_yuntu_topic_builder\n"
            f"confidence: high\n"
            f"privacy: private\n"
            f"related: []\n"
            f"---\n\n"
            f"# {topic['name']}\n\n"
            f"## Scope\n\n{topic['scope']}\n\nAliases: {aliases}\n\n"
            f"## Linked Official Docs\n\n"
            f"## What It Is\n\n"
            f"## When To Use\n\n"
            f"## How To Use\n\n"
            f"## Key Metrics / Signals\n\n"
            f"## Official Screenshots\n\n"
            f"## Ezra Usage Notes\n\n",
            encoding="utf-8",
        )
    return path


def infer_usage_items(topic: dict[str, Any], matched_text: str, article_title: str) -> dict[str, list[str]]:
    h = matched_text
    what = []
    when = []
    how = []
    metrics = []
    notes = []
    if "直播" in topic["name"]:
        what.append(f"- 用于直播诊断、直播人群、直播排品、开播策略、引流策略和场次复盘。（来源：{article_title}）")
        when.append("- 当直播间需要定位流量结构、转化效率、货品表现或开播时段问题时使用。")
        how.extend(["- 先看直播诊断定位流量进入与成交转化短板。", "- 再结合直播人群/直播排品判断人群与货品是否匹配。", "- 最后用开播策略和引流策略优化时段与流量结构。"])
    if "投广" in topic["name"]:
        what.append(f"- 用于对比行业/竞对投放情况，辅助阶段性投放规划、计划基建和创编参考。（来源：{article_title}）")
        when.append("- 当需要判断投不投、投多少、如何建计划、选什么优化目标和人群包时使用。")
        how.extend(["- 先设置行业、类目、价格带、ROI 水位等学习对象。", "- 看投广诊断判断投流比例、消耗量级、单计划跑量能力。", "- 看创编参考优化目标、推广方式、营销类型、营销目标、营销场景。"])
    if "人群" in topic["name"]:
        what.append(f"- 用于做人群资产、人群破圈、行业人群和直播人群转化分析。（来源：{article_title}）")
        when.append("- 当直播间或内容需要破圈、找高转化人群、评估自有人群/行业人群效率时使用。")
        how.extend(["- 对比自有人群、行业人群和自定义人群的转化表现。", "- 把优质人群沉淀为后续内容、直播和投放的人群包。"])
    if "商品" in topic["name"]:
        what.append(f"- 用于分析品类趋势、货盘价值、潜爆单品、卖点和价格带机会。（来源：{article_title}）")
        when.append("- 当需要选品、排品、优化货盘或定位潜爆单品时使用。")
        how.extend(["- 先看短期/长期品类趋势，再下钻赛道、商品、卖点、价格。", "- 用单品策略分析现有货盘潜力和优化建议。"])
    if "内容" in topic["name"]:
        what.append(f"- 用于从选题、素材制作和抖音号表现角度优化内容。（来源：{article_title}）")
        when.append("- 当内容量级、播放互动或素材质量落后竞品时使用。")
        how.extend(["- 看行业内容和内容榜找高潜选题/素材形态。", "- 用我的内容-抖音号分析对比竞品差距。"])
    if "行业" in topic["name"]:
        what.append(f"- 用于看行业达人、内容、热词、热点榜单和竞品账号/直播间表现。（来源：{article_title}）")
        when.append("- 当需要了解行业趋势、找达人、找热门内容或识别竞争抖音号/直播间时使用。")
        how.extend(["- 先看行业热榜/热词定位趋势，再看行业达人/内容找可参考对象。", "- 用竞争分析识别相似抖音号、相似直播间和热门商品/视频。"])
    if "搜索" in topic["name"]:
        what.append(f"- 用于查看行业热门搜索词、搜索人群、搜后看和搜后购内容。（来源：{article_title}）")
        when.append("- 当需要围绕搜索流量做选题、商品词和内容承接时使用。")
        how.append("- 优先筛选行业热门搜索词，再看搜索人群及搜后行为内容。")
    if "FAQ" in topic["name"]:
        what.append(f"- 用于官网后台问题反馈、消息中心和官方社群入口。（来源：{article_title}）")
        when.append("- 当产品使用中遇到后台问题、通知或需要官方支持时使用。")
    for metric in ["GMV", "ROI", "点击率", "点击成交率", "转化率", "互动率", "播放量", "观看人次", "新增粉丝", "消耗", "人群", "流量结构"]:
        if metric in h and f"- {metric}" not in metrics:
            metrics.append(f"- {metric}")
    if not notes:
        notes.append(f"- 回答相关问题时优先引用本专题，再回到官方文档原文核对细节。（来源：{article_title}）")
    return {"What It Is": what, "When To Use": when, "How To Use": how, "Key Metrics / Signals": metrics, "Ezra Usage Notes": notes}


def build_topics(article_path: Path, *, data_root: Path | None = None, min_score: int = 4) -> dict[str, Any]:
    root = Path(data_root).resolve() if data_root else ROOT
    article_path = (root / article_path).resolve() if not article_path.is_absolute() else article_path.resolve()
    text = article_path.read_text(encoding="utf-8")
    title = title_from_note(text, article_path)
    url = frontmatter_value(text, "url")
    sections = split_sections(text)
    changed: list[str] = []
    matched: list[dict[str, Any]] = []
    for topic in TOPICS:
        topic_sections = []
        for section in sections:
            sec_text = "\n".join(section["lines"])
            score = score_topic(section["heading"] + "\n" + sec_text, topic)
            if score >= min_score:
                topic_sections.append((section, sec_text, score))
        whole_score = score_topic(text, topic)
        if not topic_sections and whole_score < min_score:
            continue
        matched.append({"name": topic["name"], "slug": topic["slug"], "score": whole_score})
        path = ensure_topic(topic, root)
        page = path.read_text(encoding="utf-8")
        link = f"- [{title}](../../articles/sources/{article_path.name}) — {url}"
        page, c = append_unique_section(page, "Linked Official Docs", [link]); did_change = c
        combined = "\n".join(sec_text for _, sec_text, _ in topic_sections) or text
        usage = infer_usage_items(topic, combined, title)
        for heading, items in usage.items():
            page, c = append_unique_section(page, heading, items); did_change |= c
        summaries = []
        for section, sec_text, score in topic_sections[:8]:
            summary = section_summary(sec_text)
            if summary:
                summaries.append(f"- **{section['heading']}**：{summary}（来源：[{title}](../../articles/sources/{article_path.name})）")
        page, c = append_unique_section(page, "How To Use", summaries); did_change |= c
        screenshots = image_lines(combined, title)
        page, c = append_unique_section(page, "Official Screenshots", screenshots); did_change |= c
        if did_change:
            page = re.sub(r"^updated:\s*.*$", f"updated: {now_iso()}", page, count=1, flags=re.M)
            path.write_text(page, encoding="utf-8")
            changed.append(rel(root, path))
    index = root / "wiki" / "topics" / "巨量云图" / "index.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index_lines = ["# 巨量云图专题索引", "", "用于把巨量云图官方文档沉淀为可问答的专题知识页。", ""]
    for topic in TOPICS:
        p = topic_path(topic, root)
        if p.exists():
            index_lines.append(f"- [{topic['name']}]({p.name}) — {topic['scope']}")
    old = index.read_text(encoding="utf-8") if index.exists() else ""
    new = "\n".join(index_lines).rstrip() + "\n"
    if new != old:
        index.write_text(new, encoding="utf-8")
        changed.append(rel(root, index))
    return {"ok": True, "article": rel(root, article_path), "topics": matched, "changed": changed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build 巨量云图 official-document topic pages from an ingested article note.")
    parser.add_argument("--article", required=True)
    parser.add_argument("--data-dir")
    args = parser.parse_args(argv)
    result = build_topics(Path(args.article), data_root=Path(args.data_dir) if args.data_dir else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
