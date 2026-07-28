from __future__ import annotations

import importlib.util
import json
import py_compile
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRAIN_CLI = ROOT / "scripts" / "brain_cli.py"


def load_brain_cli():
    module_name = f"brain_cli_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, BRAIN_CLI)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_brain_cli_compiles() -> None:
    py_compile.compile(str(BRAIN_CLI), doraise=True)


def test_paths_routes_core_note_types() -> None:
    brain = load_brain_cli()

    assert brain.paths("expense", "2026-06-27")["path"] == "wiki/finance/expenses/2026-06.md"
    assert brain.paths("daily", "2026-06-27")["path"] == "wiki/life/daily/2026-06-27.md"
    assert brain.paths("article", "2026-06-27", "Second Brain Test")["path"] == "wiki/articles/sources/2026-06-27-second-brain-test.md"


def test_capture_preserves_raw_and_writes_finance_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.capture("今天高德打车到公司花了35元，早餐绿豆粥3元。", "telegram")

    assert result["ok"] is True
    assert "finance" in result["categories"]
    raw_files = list((tmp_path / "raw" / "telegram").glob("*.jsonl"))
    assert len(raw_files) == 1
    raw_records = [json.loads(line) for line in raw_files[0].read_text(encoding="utf-8").splitlines()]
    assert raw_records[0]["text"] == "今天高德打车到公司花了35元，早餐绿豆粥3元。"

    expense_files = list((tmp_path / "wiki" / "finance" / "expenses").glob("*.md"))
    assert len(expense_files) == 1
    expense_text = expense_files[0].read_text(encoding="utf-8")
    assert "高德打车到公司" in expense_text
    assert "35" in expense_text
    assert "早餐绿豆粥" in expense_text
    assert "3" in expense_text
    assert (tmp_path / "log.md").exists()


def test_capture_splits_loose_multi_expense_message_into_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.capture("今天高德打车花了46，星巴克21，早餐3块", "telegram")

    assert result["ok"] is True
    expense_files = list((tmp_path / "wiki" / "finance" / "expenses").glob("*.md"))
    assert len(expense_files) == 1
    expense_text = expense_files[0].read_text(encoding="utf-8")
    assert "| " + brain.today() + " | 高德打车 | 46 | commute |  | telegram |" in expense_text
    assert "| " + brain.today() + " | 星巴克 | 21 | dining |  | telegram |" in expense_text
    assert "| " + brain.today() + " | 早餐 | 3 | dining |  | telegram |" in expense_text


def test_expense_category_maps_housing_and_groceries() -> None:
    brain = load_brain_cli()

    assert brain.expense_items("花了1013.08买了眼肉牛排") == [("眼肉牛排", "1013.08")]
    assert brain.expense_category("交了房租") == "housing"
    assert brain.expense_subcategory("交了房租") == "房租"
    assert brain.expense_category("眼肉牛排") == "grocery"
    assert brain.expense_subcategory("眼肉牛排") == "肉类/牛排"
    assert brain.CATEGORY_LABELS["housing"] == "居住"
    assert brain.CATEGORY_LABELS["grocery"] == "食品生鲜"


def test_capture_syncs_real_expenses_to_lark_when_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    config = tmp_path / "config" / "brain.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "lark_expense_sync:\n"
        "  enabled: true\n"
        "  base_token: base_test\n"
        "  table_id: tbl_test\n"
        "  identity: user\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_run_lark_cli(args: list[str], timeout: int = 60):
        calls.append(args)
        if "+field-list" in args:
            return brain.subprocess.CompletedProcess(args, 0, stdout='{"ok":true,"data":{"fields":[{"name":"同步ID"},{"name":"二级分类"}]}}', stderr="")
        if "+record-search" in args:
            return brain.subprocess.CompletedProcess(args, 0, stdout='{"ok":true,"data":{"data":[],"record_id_list":[]}}', stderr="")
        if "+record-batch-create" in args:
            return brain.subprocess.CompletedProcess(args, 0, stdout='{"ok":true}', stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(brain, "run_lark_cli", fake_run_lark_cli)

    result = brain.capture("今天高德打车花了46，星巴克21", "telegram")

    assert result["ok"] is True
    assert result["lark_expense_sync"][0]["synced"] == 2
    batch_call = next(call for call in calls if "+record-batch-create" in call)
    payload = json.loads(batch_call[batch_call.index("--json") + 1])
    assert payload["fields"] == ["同步ID", "项目", "日期", "金额", "分类", "二级分类", "支付方式", "商户", "备注", "来源", "月份", "是否报销"]
    assert payload["rows"][0][1:8] == ["高德打车", f"{brain.today()} 00:00:00", 46.0, "通勤交通", "打车", "未知", "高德"]
    assert payload["rows"][1][1:8] == ["星巴克", f"{brain.today()} 00:00:00", 21.0, "外食餐饮", "咖啡饮品", "未知", "星巴克"]


def test_capture_preserves_local_data_when_lark_sync_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    config = tmp_path / "config" / "brain.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "lark_expense_sync:\n"
        "  enabled: true\n"
        "  base_token: base_test\n"
        "  table_id: tbl_test\n"
        "  identity: user\n",
        encoding="utf-8",
    )

    def failing_sync(rows: list[dict]) -> dict:
        raise RuntimeError("need_user_authorization")

    monkeypatch.setattr(brain, "sync_expenses_to_lark", failing_sync)

    result = brain.capture("今天午饭花了28元", "telegram")

    assert result["ok"] is True
    assert result["lark_expense_sync"][0]["synced"] == 0
    assert "need_user_authorization" in result["lark_expense_sync"][0]["error"]
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / f"{brain.month()}.md"
    assert "| 午饭 | 28 | dining |  | telegram |" in expense_file.read_text(encoding="utf-8")


def test_capture_from_verify_source_preserves_raw_but_skips_structured_daily_stats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.capture("验证数据：早餐花了99元，晚上23点睡觉，想到测试灵感。", "verify")

    assert result["ok"] is True
    assert result["test_source"] is True
    raw_files = list((tmp_path / "raw" / "verify").glob("*.jsonl"))
    assert len(raw_files) == 1
    assert result["files"] == [raw_files[0].relative_to(tmp_path).as_posix()]
    assert not (tmp_path / "inbox").exists()
    assert not (tmp_path / "wiki" / "finance" / "expenses").exists()
    assert not (tmp_path / "wiki" / "life" / "daily").exists()
    assert "test capture" in (tmp_path / "log.md").read_text(encoding="utf-8")


def test_query_expenses_sums_existing_month(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / "2026-06.md"
    expense_file.parent.mkdir(parents=True)
    expense_file.write_text(
        "| Date | Item | Amount | Category | Notes | Source |\n"
        "|---|---:|---:|---|---|---|\n"
        "| 2026-06-27 | 打车 | 35 | commute |  | telegram |\n"
        "| 2026-06-27 | 早餐 | 3 | food |  | telegram |\n",
        encoding="utf-8",
    )

    result = brain.query_expenses("这个月主要开销是什么", "2026-06")

    assert result["total"] == 38
    assert result["by_category"]["commute"] == 35
    assert "wiki/finance/expenses/2026-06.md" in result["answer"]


def test_query_expenses_excludes_verify_and_e2e_sources_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / "2026-06.md"
    expense_file.parent.mkdir(parents=True)
    expense_file.write_text(
        "| Date | Item | Amount | Category | Notes | Source |\n"
        "|---|---:|---:|---|---|---|\n"
        "| 2026-06-27 | 真实早餐 | 8 | food |  | telegram |\n"
        "| 2026-06-27 | 验证午餐 | 99 | food |  | verify |\n"
        "| 2026-06-27 | 端到端打车 | 88 | commute |  | e2e |\n",
        encoding="utf-8",
    )

    result = brain.query_expenses("这个月主要开销是什么", "2026-06")

    assert result["total"] == 8
    assert result["excluded_test_rows"] == 2
    assert len(result["rows"]) == 1
    assert "验证午餐" not in result["answer"]
    assert "已排除 2 条测试/验证记录" in result["answer"]


def test_query_today_excludes_verify_and_e2e_sections_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    inbox = tmp_path / "inbox" / f"{brain.today()}.md"
    inbox.parent.mkdir(parents=True)
    inbox.write_text(
        f"# Inbox {brain.today()}\n\n"
        "## 2026-06-27T10:00:00+08:00 — telegram\n\n真实记录：早餐花了8元。\n\n"
        "## 2026-06-27T10:01:00+08:00 — verify\n\n验证记录：午餐花了99元。\n\n"
        "## 2026-06-27T10:02:00+08:00 — e2e\n\n端到端验证记录。\n\n",
        encoding="utf-8",
    )
    daily = tmp_path / "wiki" / "life" / "daily" / f"{brain.today()}.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        "# Daily\n\n"
        "- 2026-06-27T10:00:00+08:00 (telegram) 真实生活记录。\n"
        "- 2026-06-27T10:01:00+08:00 (verify) 验证生活记录。\n"
        "- 2026-06-27T10:02:00+08:00 (e2e) 端到端生活记录。\n",
        encoding="utf-8",
    )

    result = brain.query_today()

    assert result["excluded_test_entries"] == 4
    assert "真实记录" in result["answer"]
    assert "真实生活记录" in result["answer"]
    assert "验证记录：午餐" not in result["answer"]
    assert "端到端验证记录" not in result["answer"]


def test_query_today_includes_yesterday_tomorrow_arrangements_from_work_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    today = brain.today()
    yesterday = (brain.now_dt().date() - timedelta(days=1)).isoformat()

    today_inbox = tmp_path / "inbox" / f"{today}.md"
    today_inbox.parent.mkdir(parents=True)
    today_inbox.write_text(f"# Inbox {today}\n\n## 2026-07-09T09:00:00+08:00 — telegram\n\n今天安排：对接直客。\n", encoding="utf-8")

    report = tmp_path / "daily" / "reports" / f"{yesterday}.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "7/8 今日复盘\n"
        "1. 完成昨日事项\n\n"
        "7/9 明日安排\n"
        "1. 跟进采买工作以及外部拍摄工作\n"
        "2. 跟进成片产出工作\n"
        "3. 完成素材投放\n",
        encoding="utf-8",
    )

    result = brain.query_notes("我今天一共有哪些安排")

    assert result["ok"] is True
    assert result["type"] == "today"
    assert "对接直客" in result["answer"]
    assert "跟进采买工作以及外部拍摄工作" in result["answer"]
    assert "跟进成片产出工作" in result["answer"]
    assert "完成素材投放" in result["answer"]
    assert f"daily/reports/{yesterday}.md" in result["files"]



def test_capture_today_arrangement_addition_feeds_work_daily_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.capture("今天安排新增：规划Q3销售计划", "telegram")

    assert result["ok"] is True
    assert "daily/work_report.jsonl" in result["files"]
    records = [json.loads(line) for line in (tmp_path / "daily" / "work_report.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["date"] == brain.today()
    assert records[0]["type"] == "plan"
    assert records[0]["summary"] == "规划Q3销售计划"
    assert records[0]["status"] == "pending"

    script_src = Path(__file__).resolve().parents[1] / "scripts" / "work_report.py"
    script_dst = tmp_path / "scripts" / "work_report.py"
    script_dst.parent.mkdir(parents=True)
    script_dst.write_text(script_src.read_text(encoding="utf-8"), encoding="utf-8")
    report = brain.query_notes("今天的日报")

    assert report["ok"] is True
    assert "规划Q3销售计划" in report["answer"]


def test_capture_tomorrow_arrangement_writes_next_day_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.capture("明天安排：规划Q3销售计划", "telegram")

    assert result["ok"] is True
    records = [json.loads(line) for line in (tmp_path / "daily" / "work_report.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["date"] == (brain.now_dt().date() + timedelta(days=1)).isoformat()
    assert records[0]["type"] == "plan"
    assert records[0]["summary"] == "规划Q3销售计划"

def test_query_notes_reads_persisted_work_daily_report_before_daily_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    report = tmp_path / "daily" / "reports" / "2026-06-27.md"
    report.parent.mkdir(parents=True)
    report.write_text("6/27 今日复盘\n1. 跟进27号拍摄工作\n\n6/28 明日安排\n1. 暂无记录\n", encoding="utf-8")
    daily = tmp_path / "wiki" / "life" / "daily" / "2026-06-27.md"
    daily.parent.mkdir(parents=True)
    daily.write_text("# Daily\n\n- 不应该优先返回这条普通日记。\n", encoding="utf-8")

    result = brain.query_notes("2026-06-27 日报")

    assert result["ok"] is True
    assert result["type"] == "work_daily_report"
    assert result["files"] == ["daily/reports/2026-06-27.md"]
    assert "跟进27号拍摄工作" in result["answer"]
    assert "普通日记" not in result["answer"]



def test_query_notes_regenerates_stale_work_daily_report_when_work_report_data_is_newer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    script_src = Path(__file__).resolve().parents[1] / "scripts" / "work_report.py"
    script_dst = tmp_path / "scripts" / "work_report.py"
    script_dst.parent.mkdir(parents=True)
    script_dst.write_text(script_src.read_text(encoding="utf-8"), encoding="utf-8")

    report = tmp_path / "daily" / "reports" / f"{brain.today()}.md"
    report.parent.mkdir(parents=True)
    report.write_text("7/11 今日复盘\n1. 旧事项\n\n7/12 明日安排\n1. 暂无记录\n", encoding="utf-8")
    data = tmp_path / "daily" / "work_report.jsonl"
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps({"date": brain.today(), "type": "plan", "summary": "规划Q3销售计划"}, ensure_ascii=False) + "\n", encoding="utf-8")

    result = brain.query_notes("今天的日报")

    assert result["ok"] is True
    assert result["type"] == "work_daily_report"
    assert result.get("generated") is True
    assert "规划Q3销售计划" in result["answer"]
    assert report.read_text(encoding="utf-8") == result["answer"].rstrip() + "\n"

def test_query_notes_generates_missing_work_daily_report_inside_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    script_src = Path(__file__).resolve().parents[1] / "scripts" / "work_report.py"
    script_dst = tmp_path / "scripts" / "work_report.py"
    script_dst.parent.mkdir(parents=True)
    script_dst.write_text(script_src.read_text(encoding="utf-8"), encoding="utf-8")
    data = tmp_path / "daily" / "work_report.jsonl"
    data.parent.mkdir(parents=True)
    data.write_text(json.dumps({"date": "2026-06-27", "type": "review", "summary": "完成直播复盘"}, ensure_ascii=False) + "\n", encoding="utf-8")

    result = brain.query_notes("2026-06-27 工作日报")

    assert result["ok"] is True
    assert result["type"] == "work_daily_report"
    assert result["generated"] is True
    assert result["files"] == ["daily/reports/2026-06-27.md"]
    assert (tmp_path / "daily" / "reports" / "2026-06-27.md").exists()
    assert "完成直播复盘" in result["answer"]


def test_query_notes_resolves_relative_work_daily_report_dates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    report_date = (brain.now_dt().date() - timedelta(days=2)).isoformat()
    report = tmp_path / "daily" / "reports" / f"{report_date}.md"
    report.parent.mkdir(parents=True)
    report.write_text("前天 今日复盘\n1. 完成前天复盘\n", encoding="utf-8")

    result = brain.query_notes("前天的日报内容是什么")

    assert result["ok"] is True
    assert result["type"] == "work_daily_report"
    assert result["date"] == report_date
    assert result["files"] == [f"daily/reports/{report_date}.md"]
    assert "完成前天复盘" in result["answer"]


def test_query_notes_offers_candidates_when_exact_topic_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    topic = tmp_path / "wiki" / "topics" / "persona-ip.md"
    topic.parent.mkdir(parents=True)
    topic.write_text("# 人设 IP\n\n## Core Claims\n\n- 人设 IP 能提升信任。\n", encoding="utf-8")
    article = tmp_path / "wiki" / "articles" / "sources" / "2026-06-28-persona-case.md"
    article.parent.mkdir(parents=True)
    article.write_text("# 人设IP案例文章\n\n人设IP 案例和直播间信任。", encoding="utf-8")

    result = brain.query_notes("人设IP指标漏斗")

    assert result["ok"] is True
    assert result["type"] == "candidates"
    assert "没有找到精确结果" in result["answer"]
    assert "你可能要找" in result["answer"]
    assert "wiki/topics/persona-ip.md" in result["answer"]
    assert "wiki/articles/sources/2026-06-28-persona-case.md" in result["answer"]


def test_query_notes_prioritizes_exact_topic_page_over_generic_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    topic = tmp_path / "wiki" / "topics" / "persona-ip.md"
    topic.parent.mkdir(parents=True)
    topic.write_text(
        "---\n"
        "id: topic-persona-ip\n"
        "type: topic\n"
        "aliases: [人设IP, 人设 IP, 创始人IP]\n"
        "---\n\n"
        "# 人设 IP\n\n"
        "## Core Claims\n\n"
        "- 人设 IP 可以缓解中小品牌/白牌的信任缺失。\n\n"
        "## Methodology\n\n"
        "- 选人 → 测试 → 放大。\n\n"
        "## Metrics\n\n"
        "- ROI\n"
        "- 自然流占比\n\n"
        "## Ezra Implications\n\n"
        "- 选主播/达人时要看可信标签和表达欲。\n",
        encoding="utf-8",
    )
    article = tmp_path / "wiki" / "articles" / "sources" / "persona.md"
    article.parent.mkdir(parents=True)
    article.write_text("# 泛搜索文章\n\n人设IP 普通匹配。", encoding="utf-8")

    result = brain.query_notes("人设IP")

    assert result["ok"] is True
    assert result["type"] == "topic"
    assert result["topic"]["title"] == "人设 IP"
    assert result["files"] == ["wiki/topics/persona-ip.md"]
    assert "## 人设 IP" in result["answer"]
    assert "Core Claims" in result["answer"]
    assert "信任缺失" in result["answer"]
    assert "Methodology" in result["answer"]
    assert "选人 → 测试 → 放大" in result["answer"]
    assert "Metrics" in result["answer"]
    assert "自然流占比" in result["answer"]
    assert "Ezra Implications" in result["answer"]
    assert "可信标签" in result["answer"]
    assert "泛搜索文章" not in result["answer"]


def test_query_notes_topic_section_filter_returns_only_requested_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    topic = tmp_path / "wiki" / "topics" / "persona-ip.md"
    topic.parent.mkdir(parents=True)
    topic.write_text(
        "# 人设 IP\n\n"
        "## Core Claims\n\n- 信任缺失。\n\n"
        "## Methodology\n\n- 选人 → 测试 → 放大。\n\n"
        "## Metrics\n\n- ROI\n- 自然流占比\n",
        encoding="utf-8",
    )

    result = brain.query_notes("人设IP 指标")

    assert result["type"] == "topic"
    assert result["topic"]["section_filter"] == "Metrics"
    assert "## 人设 IP — Metrics" in result["answer"]
    assert "ROI" in result["answer"]
    assert "自然流占比" in result["answer"]
    assert "选人 → 测试 → 放大" not in result["answer"]


def test_query_notes_matches_hierarchical_topic_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    topic = tmp_path / "wiki" / "topics" / "career-growth" / "business-thinking" / "business-accounting-profit-thinking.md"
    topic.parent.mkdir(parents=True)
    topic.write_text(
        "---\n"
        "id: topic-career-growth-business-thinking-business-accounting-profit-thinking\n"
        "type: topic\n"
        "domain: 职业成长\n"
        "parent: 经营能力\n"
        "topic_path: 职业成长/经营能力/经营核算与利润意识\n"
        "facets: [经营, 利润, 单品损益, ROI]\n"
        "aliases: [经营核算, 利润意识, 单品损益表]\n"
        "---\n\n"
        "# 经营核算与利润意识\n\n"
        "## Core Claims\n\n- ROI 不是完整经营指标。\n\n"
        "## Metrics\n\n- 保本 ROI\n- 贡献利润\n",
        encoding="utf-8",
    )

    result = brain.query_notes("职业成长 经营能力 指标")

    assert result["type"] == "topic"
    assert result["topic"]["title"] == "经营核算与利润意识"
    assert result["files"] == ["wiki/topics/career-growth/business-thinking/business-accounting-profit-thinking.md"]
    assert "保本 ROI" in result["answer"]


def test_query_notes_ignores_topic_index_pages_for_precise_topic_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    index = tmp_path / "wiki" / "topics" / "content-brand-growth" / "index.md"
    index.parent.mkdir(parents=True)
    index.write_text(
        "# 内容与品牌增长\n\n"
        "- [人设 IP](persona-content/persona-ip.md)\n"
        "- [中小品牌起盘](brand-launch/small-brand-launch.md)\n"
        "方法、指标、案例、品牌增长。\n",
        encoding="utf-8",
    )
    topic = tmp_path / "wiki" / "topics" / "content-brand-growth" / "persona-content" / "persona-ip.md"
    topic.parent.mkdir(parents=True)
    topic.write_text(
        "---\n"
        "type: topic\n"
        "domain: 内容与品牌增长\n"
        "parent: 人设内容\n"
        "topic_path: 内容与品牌增长/人设内容/人设 IP\n"
        "facets: [人设IP, 创始人IP, 信任]\n"
        "aliases: [人设IP, 人设 IP, 创始人IP]\n"
        "---\n\n"
        "# 人设 IP\n\n"
        "## Methodology\n\n- 选人 → 测试 → 放大。\n",
        encoding="utf-8",
    )

    result = brain.query_notes("内容与品牌增长 人设 方法")

    assert result["type"] == "topic"
    assert result["topic"]["title"] == "人设 IP"
    assert result["topic"]["section_filter"] == "Methodology"
    assert result["files"] == ["wiki/topics/content-brand-growth/persona-content/persona-ip.md"]
    assert "选人 → 测试 → 放大" in result["answer"]
    assert "content-brand-growth/index.md" not in result["files"]


def test_query_notes_time_filtered_articles_returns_recent_matching_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    today = brain.now_dt().date()
    recent_day = (today - timedelta(days=2)).isoformat()
    old_day = (today - timedelta(days=20)).isoformat()
    article_dir = tmp_path / "wiki" / "articles" / "sources"
    article_dir.mkdir(parents=True)
    recent = article_dir / f"{recent_day}-persona-recent.md"
    recent.write_text(
        "---\n"
        f"created: {recent_day}T10:00:00+08:00\n"
        "url: https://example.com/recent\n"
        "---\n\n"
        "# 最近人设IP文章\n\n"
        "## Executive Summary\n\n- 人设IP 最近方法。\n",
        encoding="utf-8",
    )
    old = article_dir / f"{old_day}-persona-old.md"
    old.write_text(
        "---\n"
        f"created: {old_day}T10:00:00+08:00\n"
        "url: https://example.com/old\n"
        "---\n\n"
        "# 旧人设IP文章\n\n"
        "## Executive Summary\n\n- 人设IP 旧方法。\n",
        encoding="utf-8",
    )

    result = brain.query_notes("最近7天人设IP 文章")

    assert result["ok"] is True
    assert result["type"] == "precise_source"
    assert result["source_type"] == "articles"
    assert result["time_filter"]["days"] == 7
    assert "最近人设IP文章" in result["answer"]
    assert "旧人设IP文章" not in result["answer"]
    assert result["files"] == [f"wiki/articles/sources/{recent.name}"]


def test_query_notes_source_type_action_insights_returns_article_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    article = tmp_path / "wiki" / "articles" / "sources" / "2026-06-28-persona.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\nurl: https://example.com/persona\n---\n\n"
        "# 人设IP文章\n\n"
        "## Executive Summary\n\n- 泛摘要不应该作为行动建议返回。\n\n"
        "## Actionable Insights for Ezra\n\n"
        "- 把人设内容作为千川素材测试。\n"
        "- 选主播时看可信标签和表达欲。\n",
        encoding="utf-8",
    )

    result = brain.query_notes("人设IP 行动建议")

    assert result["ok"] is True
    assert result["type"] == "precise_source"
    assert result["source_type"] == "action_insights"
    assert "把人设内容作为千川素材测试" in result["answer"]
    assert "可信标签" in result["answer"]
    assert "泛摘要不应该" not in result["answer"]
    assert result["files"] == ["wiki/articles/sources/2026-06-28-persona.md"]

def test_summary_week_creates_weekly_review_excluding_test_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    current = brain.now_dt().date()
    week_start = current - timedelta(days=current.weekday())
    day1 = week_start.isoformat()
    day2 = (week_start + timedelta(days=1)).isoformat()
    day3 = (week_start + timedelta(days=2)).isoformat()
    life_day = (week_start + timedelta(days=3)).isoformat()
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / f"{day1[:7]}.md"
    expense_file.parent.mkdir(parents=True)
    expense_file.write_text(
        "| Date | Item | Amount | Category | Notes | Source |\n"
        "|---|---:|---:|---|---|---|\n"
        f"| {day1} | 真实早餐 | 8 | food |  | telegram |\n"
        f"| {day2} | 真实打车 | 15 | commute |  | gui |\n"
        f"| {day3} | 验证午餐 | 99 | food |  | verify |\n",
        encoding="utf-8",
    )
    daily = tmp_path / "wiki" / "life" / "daily" / f"{life_day}.md"
    daily.parent.mkdir(parents=True)
    daily.write_text(
        "# Daily\n\n"
        f"- {life_day}T10:00:00+08:00 (telegram) 真实生活记录。\n"
        f"- {life_day}T10:01:00+08:00 (verify) 验证生活记录。\n",
        encoding="utf-8",
    )

    result = brain.summarize("week")

    assert result["ok"] is True
    assert result["file"].startswith("reviews/weekly/")
    review_path = tmp_path / result["file"]
    assert review_path.exists()
    review = review_path.read_text(encoding="utf-8")
    assert "# Weekly Review" in review
    assert "真实消费合计 23" in review
    assert "真实生活记录" in review
    assert "验证午餐" not in review
    assert "- 2026-06-27T10:01:00+08:00 (verify) 验证生活记录。" not in review
    assert "已排除" in review
    assert "summary generated: week" in (tmp_path / "log.md").read_text(encoding="utf-8")


def test_create_article_writes_raw_note_index_and_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.create_article(
        "https://example.com/article",
        title="Second Brain Test Article",
        content="第一段摘要。\n正文内容。",
        source="pytest",
    )

    assert result["ok"] is True
    assert "wiki/articles/index.md" in result["files"]
    note_path = tmp_path / "wiki" / "articles" / "sources" / next(f for f in result["files"] if f.startswith("wiki/articles/sources/")).split("/")[-1]
    assert note_path.exists()
    note = note_path.read_text(encoding="utf-8")
    assert "# Second Brain Test Article" in note
    assert "第一段摘要" in note
    assert (tmp_path / "raw" / "web").exists()
    assert (tmp_path / "log.md").exists()


def test_create_article_payload_v2_writes_structured_note_metadata_and_raw(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    payload = {
        "schema_version": "article-payload-v2",
        "url": "https://example.com/live-commerce",
        "title": "直播间投流复盘方法",
        "author": "Example Author",
        "published": "2026-06-27",
        "source": "web",
        "content": "第一段正文。\n第二段正文讲投流和转化率。",
        "tl_dr": "这是一篇关于直播间投流复盘的方法文章。",
        "summary": ["强调按场次复盘", "关注 GMV 和转化率"],
        "core_thesis": "投流复盘要把流量、主播状态和商品承接放在一起看。",
        "structure": ["背景", "方法", "案例"],
        "key_points": ["看转化率", "看主播状态"],
        "important_details": ["示例 GMV 8.6w"],
        "concepts": ["直播投流", "转化率"],
        "actionable_insights": ["给 3 号直播间建立投流复盘表"],
        "possible_applications": ["周复盘直播运营板块"],
        "critique": ["缺少长期数据样本"],
        "quotes": ["复盘要看承接效率。"],
        "follow_up_questions": ["3 号直播间目前最大投流浪费点是什么？"],
        "related": ["wiki/work/live-commerce/traffic-buying.md"],
        "extraction_status": "complete",
        "extraction_method": "web_extract",
    }

    result = brain.create_article("", payload=payload)

    assert result["ok"] is True
    assert result["extraction_status"] == "complete"
    assert result["extraction_method"] == "web_extract"
    assert result["word_count"] > 0
    assert result["content_hash"].startswith("sha256:")
    raw_path = tmp_path / next(f for f in result["files"] if f.startswith("raw/web/"))
    note_path = tmp_path / next(f for f in result["files"] if f.startswith("wiki/articles/sources/"))
    assert "第二段正文讲投流和转化率" in raw_path.read_text(encoding="utf-8")
    note = note_path.read_text(encoding="utf-8")
    assert "extraction_status: complete" in note
    assert "extraction_method: web_extract" in note
    assert "content_hash: sha256:" in note
    assert "## TL;DR" in note
    assert "## Actionable Insights for Ezra" in note
    assert "[[直播投流]]" in note
    assert "给 3 号直播间建立投流复盘表" in note


def test_article_cli_accepts_payload_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps({
        "schema_version": "article-payload-v2",
        "url": "https://example.com/payload",
        "title": "Payload Article",
        "content": "Payload 正文内容。",
        "extraction_status": "complete",
        "extraction_method": "manual_payload"
    }, ensure_ascii=False), encoding="utf-8")

    rc = brain.main(["article", "--url", "https://fallback.example", "--payload-json", str(payload_path)])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["title"] == "Payload Article"
    assert out["extraction_method"] == "manual_payload"


def test_correction_updates_single_matching_expense_amount_and_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / "2026-06.md"
    expense_file.parent.mkdir(parents=True)
    expense_file.write_text(
        "| Date | Item | Amount | Category | Notes | Source |\n"
        "|---|---:|---:|---|---|---|\n"
        "| 2026-06-27 | 早餐绿豆粥 | 3 | food |  | pytest |\n"
        "| 2026-06-27 | 高德打车到公司 | 35 | commute |  | pytest |\n",
        encoding="utf-8",
    )

    result = brain.correct("今天早餐不是3元，是4元")

    assert result["ok"] is True
    assert result["status"] == "corrected"
    assert result["old"] == "3"
    assert result["new"] == "4"
    assert result["files"] == ["wiki/finance/expenses/2026-06.md"]
    text = expense_file.read_text(encoding="utf-8")
    assert "| 2026-06-27 | 早餐绿豆粥 | 4 | food |  | pytest |" in text
    assert "| 2026-06-27 | 高德打车到公司 | 35 | commute |  | pytest |" in text
    assert "correction:" in (tmp_path / "log.md").read_text(encoding="utf-8")


def test_correction_returns_ambiguous_when_multiple_expenses_match_amount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    expense_file = tmp_path / "wiki" / "finance" / "expenses" / "2026-06.md"
    expense_file.parent.mkdir(parents=True)
    expense_file.write_text(
        "| Date | Item | Amount | Category | Notes | Source |\n"
        "|---|---:|---:|---|---|---|\n"
        "| 2026-06-27 | 早餐 | 3 | food |  | pytest |\n"
        "| 2026-06-27 | 饮料 | 3 | food |  | pytest |\n",
        encoding="utf-8",
    )

    result = brain.correct("今天不是3元，是4元")

    assert result["ok"] is False
    assert result["status"] == "ambiguous"
    assert len(result["candidates"]) == 2
    assert "早餐 | 3" in expense_file.read_text(encoding="utf-8")
    assert not (tmp_path / "log.md").exists()


def test_correction_updates_recent_text_value_in_daily_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)
    daily_file = tmp_path / "wiki" / "life" / "daily" / "2026-06-27.md"
    daily_file.parent.mkdir(parents=True)
    daily_file.write_text("# Daily\n\n- 备用钥匙在车库左边第一个抽屉。\n", encoding="utf-8")

    result = brain.correct("备用钥匙不是在车库左边第一个抽屉，是在鞋柜第二层")

    assert result["ok"] is True
    assert result["status"] == "corrected"
    assert "鞋柜第二层" in daily_file.read_text(encoding="utf-8")
    assert "车库左边第一个抽屉" not in daily_file.read_text(encoding="utf-8")


def test_correction_returns_not_found_when_no_record_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = load_brain_cli()
    monkeypatch.setattr(brain, "ROOT", tmp_path)

    result = brain.correct("今天早餐不是3元，是4元")

    assert result["ok"] is False
    assert result["status"] == "not_found"


