from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "juliang_yuntu_topic_builder.py"


def load_builder():
    name = f"juliang_yuntu_topic_builder_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builds_yuntu_topic_pages_from_official_doc_article(tmp_path: Path) -> None:
    builder = load_builder()
    article = tmp_path / "wiki" / "articles" / "sources" / "2026-06-30-巨量云图极速版产品使用手册.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\n"
        "url: https://bytedance.larkoffice.com/docx/doxcn-test\n"
        "source: lark_doc\n"
        "---\n\n"
        "# 巨量云图极速版产品使用手册\n\n"
        "## 直播策略\n\n"
        "### 直播诊断：提供直播场景多角度的评估 - 诊断 - 复盘优化能力\n\n"
        "直播货品复盘：诊断商品点击率 - 点击成交率 - 场均GMV分析整体直播间表现。\n"
        "图片50: 图片展示的是巨量云图中直播人群效果评估页面，呈现直播间人群和行业人群转化数据。（文件：E:/asset/050.png）\n\n"
        "### 直播排品：定位直播间货品价值\n\n"
        "通过货品和人群组合突破，提高货品成交效率。\n\n"
        "## 投广\n\n"
        "### 投广指导：通过与行业及竞对对比，指导客户进行阶段性投放规划\n\n"
        "投广诊断关注投流比例、消耗量级、单计划跑量能力、ROI 水位；创编参考包括优化目标、推广方式、营销类型、营销目标、营销场景。\n",
        encoding="utf-8",
    )

    result = builder.build_topics(article, data_root=tmp_path)

    assert result["ok"] is True
    names = {t["name"] for t in result["topics"]}
    assert "巨量云图/直播策略" in names
    assert "巨量云图/投广策略" in names
    live = tmp_path / "wiki" / "topics" / "巨量云图" / "live-strategy.md"
    ads = tmp_path / "wiki" / "topics" / "巨量云图" / "ad-strategy.md"
    assert live.exists()
    assert ads.exists()
    live_text = live.read_text(encoding="utf-8")
    assert "# 巨量云图/直播策略" in live_text
    assert "直播诊断" in live_text
    assert "图片50" in live_text
    assert "Key Metrics / Signals" in live_text
    assert "GMV" in live_text
    ads_text = ads.read_text(encoding="utf-8")
    assert "# 巨量云图/投广策略" in ads_text
    assert "投广诊断" in ads_text
    assert "优化目标" in ads_text
    assert (tmp_path / "wiki" / "topics" / "巨量云图" / "index.md").exists()


def test_builder_cli_outputs_json(tmp_path: Path) -> None:
    article = tmp_path / "wiki" / "articles" / "sources" / "yuntu.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\nurl: https://bytedance.larkoffice.com/docx/demo\n---\n\n"
        "# 巨量云图官方文档\n\n## 人群\n\n### 行业人群：多维度找行业人群，助力人群破圈\n\nA4人群、人群包、直播人群转化效率。\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(BUILDER), "--article", "wiki/articles/sources/yuntu.md", "--data-dir", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(completed.stdout)
    assert data["ok"] is True
    assert any(t["name"] == "巨量云图/人群分析" for t in data["topics"])
