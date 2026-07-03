#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIR = ROOT / "wiki" / "articles" / "sources"
TOPIC_DIR = ROOT / "wiki" / "topics"


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


TOPIC_RULES = [
    {
        "name": "抖音电商",
        "slug": "douyin-ecommerce",
        "aliases": ["抖音电商", "抖音", "Douyin", "抖音小店"],
        "keywords": ["抖音", "千川", "直播间", "GMV", "投流", "电商", "短视频"],
        "description": "抖音电商、直播带货、千川投放、内容与货架协同。",
    },
    {
        "name": "人设 IP",
        "slug": "persona-ip",
        "aliases": ["人设IP", "人设 IP", "创始人IP", "创始人 IP", "人格 IP", "IP"],
        "keywords": ["人设IP", "人设 IP", "创始人IP", "创始人 IP", "人格", "真人出镜", "信任中介"],
        "description": "创始人/专家/匠人人设 IP，用人格建立信任、内容差异化和品牌心智。",
    },
    {
        "name": "中小品牌起盘",
        "slug": "small-brand-launch",
        "aliases": ["中小品牌", "小品牌", "白牌", "品牌起盘", "0-1起盘", "0-1 起盘"],
        "keywords": ["中小品牌", "小品牌", "白牌", "起盘", "0-1", "信任缺失", "低价内卷"],
        "description": "中小品牌/白牌从 0 到 1 起盘、破局、建立差异化的策略沉淀。",
    },
    {
        "name": "直播间投流复盘",
        "slug": "live-room-ad-review",
        "aliases": ["直播间投流复盘", "直播间", "投流复盘", "千川投流"],
        "keywords": ["直播间", "投流", "千川", "ROI", "自然流", "付费流量", "转化"],
        "description": "直播间投流、自然流/付费流、ROI、转化和场次复盘。",
    },
]


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + 4 :].lstrip()
    return text


def frontmatter_value(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def title_from_note(text: str, path: Path) -> str:
    m = re.search(r"^#\s+(.+)$", strip_frontmatter(text), re.M)
    return m.group(1).strip() if m else path.stem


def section(text: str, heading: str) -> str:
    body = strip_frontmatter(text)
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", body[start:], re.M)
    end = start + nxt.start() if nxt else len(body)
    return body[start:end].strip()


def bullets_from_section(text: str, heading: str) -> list[str]:
    items: list[str] = []
    for line in section(text, heading).splitlines():
        m = re.match(r"^[-*]\s+(.+)$", line.strip())
        if m:
            item = m.group(1).strip()
            if item and not item.startswith("暂无") and not item.startswith("待整理"):
                items.append(item)
    return items


def article_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def score_topic(text: str, rule: dict) -> int:
    score = 0
    lowered = text.lower()
    for alias in rule["aliases"]:
        count = lowered.count(alias.lower())
        score += count * 3
    for keyword in rule["keywords"]:
        count = lowered.count(keyword.lower())
        score += count
    return score


def matched_topics(text: str, min_score: int = 2) -> list[dict]:
    matches = []
    for rule in TOPIC_RULES:
        score = score_topic(text, rule)
        if score >= min_score:
            item = dict(rule)
            item["score"] = score
            matches.append(item)
    return sorted(matches, key=lambda x: (-x["score"], x["name"]))


def enrich_article_note(path: Path, topics: list[dict]) -> bool:
    text = path.read_text(encoding="utf-8")
    topic_links = [f"[[{t['name']}]]" for t in topics]
    changed = False
    related_line = "related: " + json.dumps(topic_links, ensure_ascii=False)
    if re.search(r"^related:\s*\[\]\s*$", text, re.M):
        text = re.sub(r"^related:\s*\[\]\s*$", related_line, text, count=1, flags=re.M)
        changed = True
    elif not re.search(r"^related:\s*", text, re.M):
        text = text.replace("privacy: private\n", f"privacy: private\n{related_line}\n", 1)
        changed = True

    concepts_block = "\n".join(f"- [[{t['name']}]]" for t in topics)
    if "## Concepts\n" in text:
        old = section(text, "Concepts")
        existing = set(re.findall(r"\[\[(.+?)\]\]", old))
        additions = [f"- [[{t['name']}]]" for t in topics if t["name"] not in existing]
        if additions:
            new = old.rstrip() + "\n" + "\n".join(additions)
            text = text.replace(old, new, 1)
            changed = True
    else:
        text += "\n## Concepts\n\n" + concepts_block + "\n"
        changed = True

    related_block = "\n".join(f"- [[{t['name']}]]" for t in topics)
    old_related = section(text, "Related Notes")
    if old_related and ("暂无关联" in old_related or not re.search(r"\[\[", old_related)):
        text = text.replace(old_related, related_block, 1)
        changed = True
    elif "## Related Notes\n" not in text:
        text += "\n## Related Notes\n\n" + related_block + "\n"
        changed = True

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def topic_note_path(topic: dict) -> Path:
    return TOPIC_DIR / f"{topic['slug']}.md"


def ensure_topic_note(topic: dict) -> Path:
    path = topic_note_path(topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        aliases = ", ".join(topic["aliases"])
        path.write_text(
            f"---\n"
            f"id: topic-{topic['slug']}\n"
            f"created: {now_iso()}\n"
            f"updated: {now_iso()}\n"
            f"type: topic\n"
            f"category: topics\n"
            f"tags: [topic]\n"
            f"source: article_topic_enricher\n"
            f"confidence: high\n"
            f"privacy: private\n"
            f"related: []\n"
            f"---\n\n"
            f"# {topic['name']}\n\n"
            f"## Scope\n\n{topic['description']}\n\n"
            f"Aliases: {aliases}\n\n"
            f"## Linked Articles\n\n"
            f"## Key Insights\n\n"
            f"## Action Ideas\n\n"
            f"## Open Questions\n\n",
            encoding="utf-8",
        )
    return path


def append_unique_section_items(text: str, heading: str, items: list[str]) -> tuple[str, bool]:
    if not items:
        return text, False
    if f"## {heading}\n" not in text:
        text += f"\n## {heading}\n\n"
    current = section(text, heading)
    additions = [item for item in items if item and item not in current]
    if not additions:
        return text, False
    new_current = current.rstrip() + ("\n" if current.strip() else "") + "\n".join(additions) + "\n"
    if current:
        text = text.replace(current, new_current.rstrip(), 1)
    else:
        text = text.replace(f"## {heading}\n", f"## {heading}\n\n{new_current}", 1)
    return text, True


def infer_topic_knowledge(article_text: str) -> dict[str, list[str]]:
    haystack = strip_frontmatter(article_text)
    core_claims: list[str] = []
    methodology: list[str] = []
    scenarios: list[str] = []
    metrics: list[str] = []
    cases: list[str] = []
    implications: list[str] = []

    if "信任缺失" in haystack or "信任中介" in haystack:
        core_claims.append("人设 IP 可以缓解中小品牌/白牌的信任缺失，用真人与人格做信任中介。")
    if "内容同质化" in haystack or "高同质化" in haystack or "独家壁垒" in haystack:
        core_claims.append("在人货内容高度同质化时，人物经历、价值观和表达风格更难被复制，可形成差异化壁垒。")
    if "品牌资产" in haystack or "低价内卷" in haystack:
        core_claims.append("人设 IP 有助于沉淀品牌资产，减少单纯低价竞争。")

    if "选人" in haystack and "测试" in haystack and "放大" in haystack:
        methodology.append("按“选人 → 测试 → 放大”推进：先选有可信标签和表达欲的人，再测试内容/场景/形式，最后放大核心标签和信任背书。")
    if "千川" in haystack and "自然流" in haystack:
        methodology.append("把人设内容同时作为千川素材和自然流内容测试，避免只依赖单一付费流量。")
    if "真人出镜" in haystack or "可视化" in haystack:
        methodology.append("用真人出镜把原料、工艺、品控、价值观等不可见信息可视化。")

    if "中小品牌" in haystack or "白牌" in haystack:
        scenarios.append("中小品牌、白牌、缺少线下渠道或品牌沉淀的业务。")
    if "低信任" in haystack or "信任缺失" in haystack:
        scenarios.append("低信任、用户担心假货/溢价/劣质品的品类。")
    if "高同质化" in haystack or "同质化" in haystack:
        scenarios.append("商品参数、价格、素材框架容易被复制的高同质化赛道。")
    if "ROI" in haystack or "投流" in haystack or "千川" in haystack:
        scenarios.append("投流 ROI 下降、需要自然流和品牌心智补位的直播间。")

    for metric in ["ROI", "自然流占比", "直播间进入率", "转化率", "粉丝复看", "复购率", "GMV", "完播率", "互动率"]:
        if metric in haystack and metric not in metrics:
            metrics.append(metric)
    for case in ["霞湖世家", "手艺人酒", "杨博士", "FITO", "徕芬", "蒂洛薇"]:
        if case in haystack:
            cases.append(case)

    implications.extend(bullets_from_section(article_text, "Actionable Insights for Ezra")[:4])
    if "可信标签" in haystack or "表达欲" in haystack:
        implications.append("选主播/达人/出镜人时，不只看镜头表现，也要看可信标签、产品理解和表达欲。")
    if "直播间" in haystack and "自然流" in haystack:
        implications.append("直播间内容复盘要同时看自然流、付费流和人设内容对转化的影响。")

    return {
        "Core Claims": [f"- {item}" for item in dict.fromkeys(core_claims)],
        "Methodology": [f"- {item}" for item in dict.fromkeys(methodology)],
        "Applicable Scenarios": [f"- {item}" for item in dict.fromkeys(scenarios)],
        "Metrics": [f"- {item}" for item in dict.fromkeys(metrics)],
        "Cases": [f"- {item}" for item in dict.fromkeys(cases)],
        "Ezra Implications": [f"- {item}" for item in dict.fromkeys(implications)],
    }


def update_topic_note(topic: dict, article_path: Path, article_text: str) -> bool:
    path = ensure_topic_note(topic)
    text = path.read_text(encoding="utf-8")
    title = title_from_note(article_text, article_path)
    url = frontmatter_value(article_text, "url")
    rel_path = article_rel(article_path)
    link = f"- [{title}](../articles/sources/{article_path.name}) — {url}"
    summary_items = bullets_from_section(article_text, "Executive Summary")[:3]
    action_items = bullets_from_section(article_text, "Actionable Insights for Ezra")[:4]
    quote_items = bullets_from_section(article_text, "Useful Quotes")[:2]
    key_items = [f"- {item}（来源：[{title}](../articles/sources/{article_path.name})）" for item in summary_items]
    if quote_items:
        key_items.extend(f"- 引文：{item}（来源：[{title}](../articles/sources/{article_path.name})）" for item in quote_items)
    action_lines = [f"- {item}（来源：[{title}](../articles/sources/{article_path.name})）" for item in action_items]
    changed = False
    text, c = append_unique_section_items(text, "Linked Articles", [link]); changed |= c
    text, c = append_unique_section_items(text, "Key Insights", key_items); changed |= c
    text, c = append_unique_section_items(text, "Action Ideas", action_lines); changed |= c
    knowledge = infer_topic_knowledge(article_text)
    for heading, items in knowledge.items():
        text, c = append_unique_section_items(text, heading, items); changed |= c
    if rel_path not in text:
        # Safety net in case section parsing changes.
        text += f"\n<!-- linked: {rel_path} -->\n"
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def update_topics_index(topic_paths: list[Path]) -> Path:
    path = TOPIC_DIR / "index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Topics Index\n\n"
    lines = []
    for p in sorted(topic_paths, key=lambda x: x.stem):
        title = title_from_note(p.read_text(encoding="utf-8"), p)
        line = f"- [{title}]({p.name})"
        if line not in existing and line not in lines:
            lines.append(line)
    if lines:
        if not existing.endswith("\n"):
            existing += "\n"
        existing += "\n".join(lines) + "\n"
        path.write_text(existing, encoding="utf-8")
    return path


def enrich_article(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    topics = matched_topics(text)
    changed: list[str] = []
    if not topics:
        return {"ok": True, "article": article_rel(path), "topics": [], "changed": []}
    if enrich_article_note(path, topics):
        changed.append(article_rel(path))
    topic_paths = []
    for topic in topics:
        topic_path = topic_note_path(topic)
        update_topic_note(topic, path, path.read_text(encoding="utf-8"))
        topic_paths.append(topic_path)
        changed.append(article_rel(topic_path))
    index = update_topics_index(topic_paths)
    changed.append(article_rel(index))
    return {"ok": True, "article": article_rel(path), "topics": [{"name": t["name"], "score": t["score"], "file": article_rel(topic_note_path(t))} for t in topics], "changed": sorted(set(changed))}


def latest_article() -> Path:
    files = sorted(ARTICLE_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No article notes found")
    return files[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich article notes by linking them to topic pages and updating topic notes.")
    parser.add_argument("--article", help="Article note path; defaults to latest article note")
    parser.add_argument("--data-dir", help="Override second-brain root for tests/ad-hoc verification")
    args = parser.parse_args(argv)
    global ROOT, ARTICLE_DIR, TOPIC_DIR
    if args.data_dir:
        ROOT = Path(args.data_dir).resolve()
        ARTICLE_DIR = ROOT / "wiki" / "articles" / "sources"
        TOPIC_DIR = ROOT / "wiki" / "topics"
    path = Path(args.article) if args.article else latest_article()
    if not path.is_absolute():
        path = ROOT / path
    result = enrich_article(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
