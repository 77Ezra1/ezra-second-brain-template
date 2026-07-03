from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "article_payload_builder.py"


def load_builder():
    module_name = f"article_payload_builder_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_payload_from_content_file_extracts_metadata_and_sections(tmp_path: Path) -> None:
    builder = load_builder()
    content_file = tmp_path / "article.md"
    content_file.write_text(
        "# 直播间投流复盘方法\n\n"
        "作者：Ezra Lab\n"
        "发布时间：2026-06-27\n\n"
        "## 背景\n"
        "直播间投流复盘要同时看 GMV、转化率和主播状态。\n\n"
        "## 方法\n"
        "第一，按场次记录流量来源。第二，复盘商品承接。\n",
        encoding="utf-8",
    )

    payload = builder.build_payload(
        url="https://example.com/live-commerce",
        title=None,
        content=content_file.read_text(encoding="utf-8"),
        source="web_extract",
        method="web_extract",
        status="complete",
        focus="重点看它对直播间投流复盘有什么启发",
    )

    assert payload["schema_version"] == "article-payload-v2"
    assert payload["url"] == "https://example.com/live-commerce"
    assert payload["title"] == "直播间投流复盘方法"
    assert payload["author"] == "Ezra Lab"
    assert payload["published"] == "2026-06-27"
    assert payload["content"].startswith("# 直播间投流复盘方法")
    assert payload["extraction_status"] == "complete"
    assert payload["extraction_method"] == "web_extract"
    assert payload["word_count"] > 0
    assert payload["content_hash"].startswith("sha256:")
    assert "GMV" in "\n".join(payload["key_points"])
    assert "直播间投流复盘" in payload["concepts"]
    assert any("直播间" in item for item in payload["actionable_insights"])


def test_build_payload_prioritizes_core_thesis_over_intro_chatter() -> None:
    builder = load_builder()
    content = """
最近忙着做 618 战役，加上没什么表达欲，因此断更了一阵子
今天这篇文章，主要是在做行业分析的时候，看到一个案例。
观点很简单，就是标题想讲的——中小品牌做抖音，人设IP是杀出重围的终极武器！
当下的抖音电商，极度内卷，常规的竞争手段很多杠杆已经有限了。
时代还给小品牌、白牌留有一条生路——创始人IP。
人设 IP 在抖音能破局的四大底层逻辑
1、人设解决中小品牌的最大痛点 —— 信任缺失
2、对抗内容同质化，构建独家壁垒
3：流量成本降低，自然流+付费流量两手抓
4：沉淀品牌资产，摆脱低价内卷
其实简单总结起来就三个步骤：选人——测试——放大
"""

    payload = builder.build_payload(
        url="https://mp.weixin.qq.com/s/example",
        title="中小品牌做抖音，人设IP是杀出重围的终极武器！",
        content=content,
        method="web_extract_playwright",
        focus="提炼对抖音直播业务可落地的方法",
    )

    assert "最近忙着" not in payload["tl_dr"]
    assert "人设IP" in payload["tl_dr"] or "创始人IP" in payload["tl_dr"]
    assert "中小品牌" in payload["core_thesis"] and "抖音" in payload["core_thesis"]
    assert any("信任缺失" in item for item in payload["summary"])
    assert any("选人" in item and "测试" in item and "放大" in item for item in payload["key_points"])
    assert {"人设 IP", "抖音电商", "中小品牌起盘", "直播间投流复盘"}.issubset(set(payload["concepts"]))
    assert any("选人-测试-放大" in item or "选人——测试——放大" in item for item in payload["actionable_insights"])


def test_builder_cli_writes_payload_json(tmp_path: Path) -> None:
    content_file = tmp_path / "article.md"
    output = tmp_path / "payload.json"
    content_file.write_text("# Payload CLI Article\n\n正文内容讲第二大脑和 Wiki 沉淀。", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--url",
            "https://example.com/payload-cli",
            "--content-file",
            str(content_file),
            "--output",
            str(output),
            "--source",
            "web_extract",
            "--method",
            "web_extract",
            "--status",
            "complete",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    stdout = json.loads(completed.stdout)
    assert stdout["ok"] is True
    assert stdout["output"] == str(output)
    assert data["title"] == "Payload CLI Article"
    assert data["extraction_status"] == "complete"
    assert data["extraction_method"] == "web_extract"
    assert data["content_hash"].startswith("sha256:")
