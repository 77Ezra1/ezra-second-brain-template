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


TOPIC_RULES = [{"name": "抖音电商",
  "slug": "douyin-ecommerce",
  "path": "live-commerce/douyin/douyin-ecommerce.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "抖音电商",
  "facets": ["抖音", "直播带货", "千川", "货架", "内容电商"],
  "aliases": ["抖音电商", "Douyin", "抖音小店", "抖音"],
  "keywords": ["抖音电商", "抖音", "抖音小店", "千川", "巨量千川", "直播带货", "直播间", "内容电商", "货架场", "短视频带货", "GMV"],
  "description": "抖音电商、直播带货、短视频带货、千川投放、内容与货架协同。"},
 {"name": "直播间投流复盘",
  "slug": "live-room-ad-review",
  "path": "live-commerce/live-review/live-room-ad-review.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "直播复盘",
  "facets": ["直播间", "投流", "千川", "ROI", "场次复盘"],
  "aliases": ["直播间投流复盘", "投流复盘", "千川投流"],
  "keywords": ["直播间投流", "场次复盘", "千川投流", "ROI", "自然流", "付费流量", "投产", "转化率", "直播间进入率", "成交密度"],
  "description": "直播间投流、自然流/付费流、ROI、转化和场次复盘。"},
 {"name": "直播间货盘与成交承接",
  "slug": "live-room-offer-conversion",
  "path": "live-commerce/live-review/live-room-offer-conversion.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "直播复盘",
  "facets": ["货盘", "商品承接", "价格机制", "购物车", "成交转化"],
  "aliases": ["货盘承接", "成交承接", "直播间货盘", "商品承接"],
  "keywords": ["货盘", "组品", "价格机制", "到手价", "购物车", "买哪组", "SKU", "利益点", "成交承接", "转化接住", "理解落差"],
  "description": "直播间/短视频把用户兴趣承接为下单的货盘、价格、SKU 与购物车设计。"},
 {"name": "短视频挂车成交素材",
  "slug": "short-video-cart-conversion-material",
  "path": "live-commerce/short-video/short-video-cart-conversion-material.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "短视频带货",
  "facets": ["挂车素材", "购物车", "短视频成交", "素材爆量"],
  "aliases": ["挂车素材", "挂车视频", "购物车素材", "短视频挂车", "带货短视频"],
  "keywords": ["挂车素材", "挂购物车", "挂车视频", "购物车", "短视频带货", "点进购物车", "成交判断", "看完下单", "爆量素材", "放量", "退款"],
  "description": "短视频挂车素材如何完成停留、商品识别、信任、价格理解与下单动作。"},
 {"name": "KOC 达人种草与出单",
  "slug": "koc-seeding-conversion",
  "path": "live-commerce/creator-marketing/koc-seeding-conversion.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "达人营销",
  "facets": ["KOC", "达人种草", "出单", "真实体验"],
  "aliases": ["KOC种草", "KOC 达人", "KOC出单", "KOC挂车"],
  "keywords": ["KOC", "达人种草", "素人种草", "真实体验", "出单", "挂车", "达人", "种草视频", "达人矩阵", "样品"],
  "description": "KOC/素人/中腰部达人种草、挂车、内容可信度与出单复盘。"},
 {"name": "达人营销与达人优选",
  "slug": "creator-marketing-selection",
  "path": "live-commerce/creator-marketing/creator-marketing-selection.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "达人营销",
  "facets": ["达人营销", "达人优选", "达人画像", "营销概览"],
  "aliases": ["达人营销", "达人优选", "达人投放", "达人合作"],
  "keywords": ["达人营销", "达人优选", "达人画像", "星图", "达人合作", "营销概览", "爆文加热", "种草通", "达人筛选", "达人复盘"],
  "description": "达人筛选、合作、投放、复盘、指标口径与达人营销工具方法。"},
 {"name": "内容种草与信任转化",
  "slug": "content-seeding-trust-conversion",
  "path": "content-brand-growth/content-seeding/content-seeding-trust-conversion.md",
  "level": 3,
  "domain": "内容与品牌增长",
  "parent": "内容种草",
  "facets": ["内容种草", "信任", "即时转化", "购买判断"],
  "aliases": ["内容种草", "种草内容", "信任转化", "购买判断"],
  "keywords": ["内容种草", "种草", "即时信任", "购买判断", "信任", "场景", "痛点", "卖点", "价值感", "靠不靠谱", "值不值得买"],
  "description": "内容如何完成种草、信任建立、购买理由、即时转化或后续搜索/直播间承接。"},
 {"name": "人设 IP",
  "slug": "persona-ip",
  "path": "content-brand-growth/persona-content/persona-ip.md",
  "level": 3,
  "domain": "内容与品牌增长",
  "parent": "人设内容",
  "facets": ["人设IP", "创始人IP", "信任", "真人出镜"],
  "aliases": ["人设IP", "人设 IP", "创始人IP", "创始人 IP", "人格 IP"],
  "keywords": ["人设IP", "人设 IP", "IP", "创始人IP", "创始人 IP", "人格", "真人出镜", "信任中介", "可信标签", "表达欲"],
  "description": "创始人/专家/匠人人设 IP，用人格建立信任、内容差异化和品牌心智。"},
 {"name": "中小品牌起盘",
  "slug": "small-brand-launch",
  "path": "content-brand-growth/brand-launch/small-brand-launch.md",
  "level": 3,
  "domain": "内容与品牌增长",
  "parent": "品牌起盘",
  "facets": ["中小品牌", "白牌", "0-1", "起盘", "破局"],
  "aliases": ["中小品牌", "小品牌", "白牌", "品牌起盘", "0-1起盘", "0-1 起盘"],
  "keywords": ["中小品牌", "小品牌", "白牌", "起盘", "0-1", "信任缺失", "低价内卷", "品牌化", "破局", "差异化"],
  "description": "中小品牌/白牌从 0 到 1 起盘、破局、建立差异化的策略沉淀。"},
 {"name": "白牌进阶品牌化",
  "slug": "white-label-brand-upgrade",
  "path": "content-brand-growth/brand-launch/white-label-brand-upgrade.md",
  "level": 3,
  "domain": "内容与品牌增长",
  "parent": "品牌起盘",
  "facets": ["白牌", "品牌化", "信任资产", "长期主义"],
  "aliases": ["白牌品牌化", "白牌进阶", "品牌升级"],
  "keywords": ["白牌", "品牌化", "品牌资产", "品牌升级", "低价内卷", "供应链品牌", "品类心智", "信任资产", "复购"],
  "description": "白牌从流量/低价生意升级为品牌资产、用户信任与长期复购的路径。"},
 {"name": "品牌部与电商部协同",
  "slug": "brand-ecommerce-team-alignment",
  "path": "content-brand-growth/org-alignment/brand-ecommerce-team-alignment.md",
  "level": 3,
  "domain": "内容与品牌增长",
  "parent": "组织协同",
  "facets": ["品牌部", "电商部", "预算", "组织协同"],
  "aliases": ["品牌电商协同", "品牌部电商部", "品效协同"],
  "keywords": ["品牌部", "电商部", "品效协同", "预算", "组织协同", "内容电商", "品牌预算", "电商业务", "部门打架"],
  "description": "品牌团队与电商团队在预算、内容、转化、品牌资产和组织目标上的协同。"},
 {"name": "明星营销与内容电商适配",
  "slug": "celebrity-marketing-content-commerce",
  "path": "content-brand-growth/celebrity-marketing/celebrity-marketing-content-commerce.md",
  "level": 3,
  "domain": "内容与品牌增长",
  "parent": "明星营销",
  "facets": ["明星营销", "切片", "内容电商", "信任"],
  "aliases": ["明星营销", "明星切片", "明星信息流"],
  "keywords": ["明星营销", "明星切片", "明星信息流", "代言", "内容电商", "水土不服", "切片", "品牌背书", "即时信任"],
  "description": "明星营销、明星切片、信息流素材在内容电商中的适配、失效与改造。"},
 {"name": "服务商选择与治理",
  "slug": "service-provider-selection-governance",
  "path": "live-commerce/operations/service-provider-selection-governance.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "经营运营",
  "facets": ["服务商", "代运营", "治理", "评估"],
  "aliases": ["抖音服务商", "服务商选择", "代运营"],
  "keywords": ["服务商", "代运营", "抖音服务商", "乙方", "靠谱", "操盘手", "交付", "坑", "治理", "评估"],
  "description": "抖音/直播电商服务商、代运营、操盘团队选择、评估和治理。"},
 {"name": "内容团队利润化管理",
  "slug": "content-team-profit-management",
  "path": "live-commerce/content-team/content-team-profit-management.md",
  "level": 3,
  "domain": "直播电商经营",
  "parent": "内容团队管理",
  "facets": ["内容团队", "利润", "成本", "人效"],
  "aliases": ["内容团队利润化", "内容团队管理", "内容团队"],
  "keywords": ["内容团队", "利润化", "成本", "人效", "内容产能", "剪辑", "编导", "素材产出", "投放素材", "利润"],
  "description": "内容团队从产出部门升级为利润中心：人效、成本、素材收益、流程与复盘。"},
 {"name": "巨量云图/5A人群资产",
  "slug": "juliang-yuntu-5a-audience-assets",
  "path": "data-tools/juliang-yuntu/5a-audience-assets.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["5A", "O-5A", "SPU 5A", "人群资产"],
  "aliases": ["5A模型", "O-5A", "SPU5A", "SPU 5A"],
  "keywords": ["5A模型", "O-5A", "SPU5A", "SPU 5A", "关系资产", "GMV to 5A"],
  "description": "巨量云图 5A/O-5A/SPU5A 人群资产、成交路径、预算拆解与关系资产经营。"},
 {"name": "巨量云图/看搜买与搜索归因",
  "slug": "juliang-yuntu-search-buy-attribution",
  "path": "data-tools/juliang-yuntu/search-buy-attribution.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["看搜买", "搜索词", "回搜", "搜索归因"],
  "aliases": ["看搜买", "看后搜", "回搜", "品牌搜索"],
  "keywords": ["看搜买", "看后搜", "回搜", "品牌搜索", "搜索词", "搜索词打标", "内容策略", "搜索归因", "搜索策略"],
  "description": "看后搜/回搜/搜索词打标/品牌搜索，用搜索行为反推内容与转化策略。"},
 {"name": "巨量云图/内容洞察与素材分析",
  "slug": "juliang-yuntu-content-insight-material-analysis",
  "path": "data-tools/juliang-yuntu/content-insight-material-analysis.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["内容洞察", "素材分析", "IDEA", "热点"],
  "aliases": ["内容洞察", "内容拆解", "素材分析", "品牌素材分析", "内容实验室"],
  "keywords": ["内容洞察", "内容拆解", "素材分析", "品牌素材分析", "IDEA", "内容实验室", "自定义内容洞察", "热点洞察", "爆单内容直播间", "卖点可视化"],
  "description": "巨量云图内容模块、素材分析、内容实验室、热点/卖点洞察与素材优化。"},
 {"name": "巨量云图/商品与爆品分析",
  "slug": "juliang-yuntu-product-hit-analysis",
  "path": "data-tools/juliang-yuntu/product-hit-analysis.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["商品", "单品", "爆品", "SPU"],
  "aliases": ["商品分析", "单品分析", "爆品指数", "商品概览"],
  "keywords": ["商品分析", "单品分析", "商品概览", "爆品指数", "SPU", "卖点", "货盘", "爆品", "单品历史生意复盘", "商品策略"],
  "description": "巨量云图商品/单品/SPU/爆品指数/卖点与历史生意复盘。"},
 {"name": "巨量云图/行业趋势与竞品洞察",
  "slug": "juliang-yuntu-industry-trend-competition",
  "path": "data-tools/juliang-yuntu/industry-trend-competition.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["行业洞察", "趋势", "竞品", "细分市场"],
  "aliases": ["行业洞察", "趋势洞察", "细分市场", "竞品分析"],
  "keywords": ["行业洞察", "趋势洞察", "细分市场", "竞品", "竞争分析", "机会人群", "行业对比", "跨行业人群", "热榜", "时令作战室"],
  "description": "行业趋势、细分市场、竞品/机会人群与时令场景的业务判断。"},
 {"name": "巨量云图/投后结案与全域度量",
  "slug": "juliang-yuntu-post-campaign-measurement",
  "path": "data-tools/juliang-yuntu/post-campaign-measurement.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["结案报告", "全域度量", "增效洞察", "触点效能"],
  "aliases": ["投后结案", "结案报告", "全域度量", "触点效能", "增效洞察"],
  "keywords": ["投后结案", "结案报告", "全域价值度量", "全域度量", "触点效能", "增效洞察", "触点组合分析", "转化助攻", "触点协同", "LBS分析", "数据回传"],
  "description": "投后结案、全域价值度量、触点效能、转化助攻、增效洞察与数据回传。"},
 {"name": "巨量云图/数据工厂与建模出价",
  "slug": "juliang-yuntu-data-factory-model-bidding",
  "path": "data-tools/juliang-yuntu/data-factory-model-bidding.md",
  "level": 3,
  "domain": "数据工具与平台方法",
  "parent": "巨量云图",
  "facets": ["数据工厂", "数据融合", "建模预测", "出价策略"],
  "aliases": ["数据工厂", "数据融合", "建模预测", "出价策略", "标签工厂"],
  "keywords": ["数据工厂", "数据融合", "标签工厂", "建模预测", "出价策略", "模型后验", "分人群包出价", "人群包", "DMP", "数据回传"],
  "description": "巨量云图数据工厂、标签工厂、数据融合、建模预测、模型后验和分人群包出价。"},
 {"name": "AI Agent 产品设计",
  "slug": "ai-agent-product-design",
  "path": "ai-agent-products/agent-product-design/ai-agent-product-design.md",
  "level": 3,
  "domain": "AI Agent 与工具产品",
  "parent": "Agent 产品设计",
  "facets": ["AI Agent", "多 Agent", "项目级记忆", "工具产品"],
  "aliases": ["AI Agent 产品", "Agent 产品设计", "AI工作台", "多Agent"],
  "keywords": ["AI Agent",
               "多 Agent",
               "多Agent",
               "项目级记忆",
               "工具调用",
               "Loop Engineering",
               "Codex",
               "Claude Code",
               "OpenCode"],
  "description": "AI Agent 工作台、项目级记忆、上下文连续性、工具调用和多 Agent 协作产品设计。"},
 {"name": "职业能力成长路径",
  "slug": "career-growth-path",
  "path": "career-growth/career-ability/career-growth-path.md",
  "level": 3,
  "domain": "职业成长",
  "parent": "职业能力",
  "facets": ["职业能力", "成长路径", "复盘", "能力诊断"],
  "aliases": ["职业成长"],
  "keywords": ["能力诊断", "职业复盘", "试用期", "成长计划", "短板", "优势"],
  "description": "个人职业能力诊断、成长路径、阶段复盘与能力补齐。"},
 {"name": "主管到经理到总监的能力跃迁",
  "slug": "supervisor-manager-director-upgrade",
  "path": "career-growth/management-upgrade/supervisor-manager-director-upgrade.md",
  "level": 3,
  "domain": "职业成长",
  "parent": "管理跃迁",
  "facets": ["主管", "经理", "总监", "管理跃迁"],
  "aliases": ["管理跃迁", "主管到经理", "经理到总监", "品牌总监"],
  "keywords": ["主管", "经理", "总监", "管理跃迁", "品牌总监", "试用期", "站稳脚跟", "向上管理", "战略", "经营型管理"],
  "description": "从执行/主管到经理/总监的管理视角、经营视角和组织能力跃迁。"},
 {"name": "经营核算与利润意识",
  "slug": "business-accounting-profit-thinking",
  "path": "career-growth/business-thinking/business-accounting-profit-thinking.md",
  "level": 3,
  "domain": "职业成长",
  "parent": "经营能力",
  "facets": ["经营", "利润", "ROI", "核算"],
  "aliases": ["经营核算", "利润意识", "经营意识"],
  "keywords": ["经营核算", "利润意识", "ROI", "毛利", "净利", "成本", "预算", "人效", "投产", "单品损益", "经营意识"],
  "description": "经营核算、利润意识、ROI、预算、人效与业务决策。"}]

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


def matched_topics(text: str, min_score: int = 5) -> list[dict]:
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
    related_match = re.search(r"^related:\s*(.*)$", text, re.M)
    if related_match:
        existing_links = re.findall(r"\[\[[^\]]+\]\]", related_match.group(1))
        merged_links = list(dict.fromkeys(existing_links + topic_links))
        merged_line = "related: " + json.dumps(merged_links, ensure_ascii=False)
        if merged_line != related_match.group(0):
            text = text[:related_match.start()] + merged_line + text[related_match.end():]
            changed = True
    else:
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
    return TOPIC_DIR / topic.get("path", f"{topic['slug']}.md")


def topic_article_link(topic_path: Path, article_path: Path) -> str:
    target = ROOT / "wiki" / "articles" / "sources" / article_path.name
    rel_path = Path(__import__("os").path.relpath(target, topic_path.parent)).as_posix()
    return rel_path


def ensure_topic_note(topic: dict) -> Path:
    path = topic_note_path(topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        aliases = ", ".join(topic["aliases"])
        topic_path = f"{topic.get('domain', '')}/{topic.get('parent', '')}/{topic['name']}".strip("/")
        facets = ", ".join(topic.get("facets", []))
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
            f"level: {topic.get('level', 3)}\n"
            f"domain: {topic.get('domain', '')}\n"
            f"parent: {topic.get('parent', '')}\n"
            f"topic_path: {topic_path}\n"
            f"facets: [{facets}]\n"
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
    link = f"- [{title}]({topic_article_link(path, article_path)}) — {url}"
    summary_items = bullets_from_section(article_text, "Executive Summary")[:3]
    action_items = bullets_from_section(article_text, "Actionable Insights for Ezra")[:4]
    quote_items = bullets_from_section(article_text, "Useful Quotes")[:2]
    article_link = topic_article_link(path, article_path)
    key_items = [f"- {item}（来源：[{title}]({article_link})）" for item in summary_items]
    if quote_items:
        key_items.extend(f"- 引文：{item}（来源：[{title}]({article_link})）" for item in quote_items)
    action_lines = [f"- {item}（来源：[{title}]({article_link})）" for item in action_items]
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
        line = f"- [{title}]({p.relative_to(TOPIC_DIR).as_posix()})"
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
