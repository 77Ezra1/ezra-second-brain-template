from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENRICHER = ROOT / "scripts" / "article_topic_enricher.py"


def load_enricher():
    module_name = f"article_topic_enricher_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, ENRICHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_matched_topics_detects_douyin_persona_and_brand_launch() -> None:
    enricher = load_enricher()
    text = "中小品牌做抖音，人设IP 是破局方法。直播间靠千川投流和自然流结合，解决白牌信任缺失。"

    topics = enricher.matched_topics(text)
    names = [t["name"] for t in topics]

    assert "抖音电商" in names
    assert "人设 IP" in names
    assert "中小品牌起盘" in names
    assert "直播间投流复盘" in names


def test_enrich_article_updates_article_and_topic_pages(tmp_path: Path, monkeypatch) -> None:
    enricher = load_enricher()
    monkeypatch.setattr(enricher, "ROOT", tmp_path)
    monkeypatch.setattr(enricher, "ARTICLE_DIR", tmp_path / "wiki" / "articles" / "sources")
    monkeypatch.setattr(enricher, "TOPIC_DIR", tmp_path / "wiki" / "topics")
    article = tmp_path / "wiki" / "articles" / "sources" / "2026-06-28-persona-ip.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\n"
        "url: https://mp.weixin.qq.com/s/test\n"
        "related: []\n"
        "---\n\n"
        "# 中小品牌做抖音，人设IP是杀出重围的终极武器！\n\n"
        "## Source Excerpt\n\n"
        "中小品牌做抖音，要靠创始人IP解决信任缺失。直播间和千川投流可以配合自然流。\n"
        "霞湖世家、手艺人酒、杨博士、FITO、徕芬都说明真人 IP 可以沉淀品牌资产。\n\n"
        "## Executive Summary\n\n"
        "- 人设 IP 用人格做信任中介。\n"
        "- 抖音直播间需要自然流和付费流量两手抓。\n\n"
        "## Concepts\n\n"
        "- [[直播间投流复盘]]\n\n"
        "## Actionable Insights for Ezra\n\n"
        "- 把创始人 IP 拆成直播间短视频素材测试清单。\n\n"
        "## Useful Quotes\n\n"
        "- 人设IP是杀出重围的终极武器。\n\n"
        "## Related Notes\n\n"
        "- 暂无关联。\n",
        encoding="utf-8",
    )

    result = enricher.enrich_article(article)

    assert result["ok"] is True
    topic_names = {t["name"] for t in result["topics"]}
    assert {"抖音电商", "人设 IP", "中小品牌起盘", "直播间投流复盘"}.issubset(topic_names)
    article_text = article.read_text(encoding="utf-8")
    assert "[[抖音电商]]" in article_text
    assert "[[人设 IP]]" in article_text
    assert "related: [" in article_text
    topic_file = tmp_path / "wiki" / "topics" / "persona-ip.md"
    assert topic_file.exists()
    topic_text = topic_file.read_text(encoding="utf-8")
    assert "# 人设 IP" in topic_text
    assert "中小品牌做抖音" in topic_text
    assert "把创始人 IP 拆成直播间短视频素材测试清单" in topic_text
    assert (tmp_path / "wiki" / "topics" / "index.md").exists()


def test_topic_page_gets_method_scenarios_metrics_and_cases(tmp_path: Path, monkeypatch) -> None:
    enricher = load_enricher()
    monkeypatch.setattr(enricher, "ROOT", tmp_path)
    monkeypatch.setattr(enricher, "ARTICLE_DIR", tmp_path / "wiki" / "articles" / "sources")
    monkeypatch.setattr(enricher, "TOPIC_DIR", tmp_path / "wiki" / "topics")
    article = tmp_path / "wiki" / "articles" / "sources" / "persona-method.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\nurl: https://example.com/persona\nrelated: []\n---\n\n"
        "# 中小品牌做抖音，人设IP是杀出重围的终极武器！\n\n"
        "## Source Excerpt\n\n"
        "中小品牌和白牌在低信任、高同质化赛道，应该用创始人IP真人出镜，把工艺、品控和价值观可视化。\n"
        "具体打法是选人、测试、放大；内容可以同时作为千川素材与自然流内容测试。\n"
        "需要观察 ROI、自然流占比、直播间进入率、转化率、粉丝复看。\n"
        "案例包括霞湖世家、手艺人酒、杨博士、FITO、徕芬、蒂洛薇。\n\n"
        "## Executive Summary\n\n- 人设 IP 解决信任缺失。\n\n"
        "## Actionable Insights for Ezra\n\n- 选主播/达人时要看可信标签和表达欲。\n",
        encoding="utf-8",
    )

    enricher.enrich_article(article)

    topic_text = (tmp_path / "wiki" / "topics" / "persona-ip.md").read_text(encoding="utf-8")
    assert "## Core Claims" in topic_text
    assert "解决信任缺失" in topic_text
    assert "## Methodology" in topic_text
    assert "选人" in topic_text and "测试" in topic_text and "放大" in topic_text
    assert "## Applicable Scenarios" in topic_text
    assert "低信任" in topic_text and "高同质化" in topic_text
    assert "## Metrics" in topic_text
    assert "ROI" in topic_text and "自然流占比" in topic_text and "粉丝复看" in topic_text
    assert "## Cases" in topic_text
    assert "霞湖世家" in topic_text and "徕芬" in topic_text
    assert "## Ezra Implications" in topic_text
    assert "可信标签" in topic_text


def test_enricher_cli_outputs_json(tmp_path: Path) -> None:
    article = tmp_path / "wiki" / "articles" / "sources" / "article.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\nurl: https://example.com\nrelated: []\n---\n\n"
        "# 抖音人设IP文章\n\n"
        "## Source Excerpt\n\n中小品牌在抖音靠人设IP和直播间自然流破局。\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(ENRICHER), "--article", "wiki/articles/sources/article.md", "--data-dir", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(completed.stdout)
    assert data["ok"] is True
    assert any(t["name"] == "抖音电商" for t in data["topics"])
