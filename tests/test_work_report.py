from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK_REPORT = ROOT / "scripts" / "work_report.py"


def load_work_report():
    module_name = f"work_report_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, WORK_REPORT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_work_report_persists_generated_report_inside_repo_root(tmp_path: Path) -> None:
    wr = load_work_report()
    wr.ROOT = tmp_path
    wr.REPORT_PATH = tmp_path / "daily" / "work_report.jsonl"
    wr.REPORT_PATH.parent.mkdir(parents=True)
    wr.REPORT_PATH.write_text(
        json.dumps(
            {
                "id": "r1",
                "created_at": "2026-06-27T18:00:00+08:00",
                "date": "2026-06-27",
                "type": "review",
                "title": "跟进拍摄工作",
                "summary": "跟进拍摄工作",
                "details": "",
                "status": "done",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    content = wr.generate_report("2026-06-27", "2026-06-28", save=True)

    saved = tmp_path / "daily" / "reports" / "2026-06-27.md"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == content.rstrip() + "\n"
    assert "6/27 今日复盘" in content
    assert "跟进拍摄工作" in content


def test_work_report_historical_plan_items_surface_as_review_when_no_done_records(tmp_path: Path) -> None:
    wr = load_work_report()
    wr.ROOT = tmp_path
    wr.REPORT_PATH = tmp_path / "daily" / "work_report.jsonl"
    wr.REPORT_PATH.parent.mkdir(parents=True)
    records = [
        {
            "id": "p1",
            "created_at": "2026-06-26T19:40:35+08:00",
            "date": "2026-06-27",
            "type": "plan",
            "title": "跟进拍摄工作",
            "summary": "跟进27号拍摄工作",
            "details": "明天跟进27号拍摄执行情况。",
            "status": "pending",
        },
        {
            "id": "p2",
            "created_at": "2026-06-26T19:40:35+08:00",
            "date": "2026-06-27",
            "type": "plan",
            "title": "跟进素材产出工作",
            "summary": "跟进素材产出工作",
            "details": "明天跟进素材产出进度和交付情况。",
            "status": "pending",
        },
    ]
    wr.REPORT_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")

    content = wr.generate_report("2026-06-27", "2026-06-28", save=True)

    assert "6/27 今日复盘" in content
    assert "1. 跟进27号拍摄工作" in content
    assert "2. 跟进素材产出工作" in content
    assert "6/28 明日安排" in content
    assert (tmp_path / "daily" / "reports" / "2026-06-27.md").exists()


def test_work_report_keeps_enough_context_for_distinct_work_situations(tmp_path: Path) -> None:
    wr = load_work_report()
    wr.ROOT = tmp_path
    wr.REPORT_PATH = tmp_path / "daily" / "work_report.jsonl"
    wr.REPORT_PATH.parent.mkdir(parents=True)
    records = [
        {
            "id": "r1",
            "created_at": "2026-06-29T18:34:53+08:00",
            "date": "2026-06-29",
            "type": "review",
            "summary": "拉组会复盘前天进度与当天安排",
        },
        {
            "id": "r2",
            "created_at": "2026-06-29T18:34:53+08:00",
            "date": "2026-06-29",
            "type": "review",
            "summary": "提供竞品星图达人并沟通BD事项",
        },
        {
            "id": "p1",
            "created_at": "2026-06-29T18:34:53+08:00",
            "date": "2026-06-30",
            "type": "plan",
            "summary": "早上周会复盘，下午拉齐脚本沟通",
        },
    ]
    wr.REPORT_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")

    content = wr.generate_report("2026-06-29", "2026-06-30", save=True)

    assert "拉组会复盘前天进度与当天安排" in content
    assert "提供竞品星图达人并沟通BD事项" in content
    assert "早上周会复盘，下午拉齐脚本沟通" in content


def test_work_report_cli_uses_repo_root_by_default(tmp_path: Path) -> None:
    # Copy the repository script into a mini repo layout and verify default ROOT
    # resolves relative to the script's parent directory, not Documents/legacy paths.
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "work_report.py"
    script.write_text(WORK_REPORT.read_text(encoding="utf-8"), encoding="utf-8")
    data = tmp_path / "daily" / "work_report.jsonl"
    data.parent.mkdir()
    data.write_text(
        json.dumps(
            {
                "id": "r1",
                "created_at": "2026-06-27T18:00:00+08:00",
                "date": "2026-06-27",
                "type": "review",
                "summary": "跟进拍摄工作",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(script), "--review-day", "2026-06-27", "--plan-day", "2026-06-28"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "跟进拍摄工作" in completed.stdout
    assert (tmp_path / "daily" / "reports" / "2026-06-27.md").exists()


def test_brain_capture_syncs_work_arrangement_to_work_report(tmp_path: Path) -> None:
    brain_path = ROOT / "scripts" / "brain_cli.py"
    module_name = f"brain_cli_work_report_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, brain_path)
    assert spec and spec.loader
    brain = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(brain)
    brain.ROOT = tmp_path

    result = brain.capture("我早上开了早会，复盘了团队昨天的工作进度以及安排了团队今天的工作", "telegram")

    assert result["ok"] is True
    report_data = tmp_path / "daily" / "work_report.jsonl"
    assert report_data.exists()
    text = report_data.read_text(encoding="utf-8")
    assert "早会复盘团队进度并安排今日工作" in text


def test_brain_capture_splits_work_arrangement_segments(tmp_path: Path) -> None:
    brain_path = ROOT / "scripts" / "brain_cli.py"
    module_name = f"brain_cli_work_report_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, brain_path)
    assert spec and spec.loader
    brain = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(brain)
    brain.ROOT = tmp_path

    brain.capture("外脑，记一下我今天的工作安排，沟通了外部拍摄需求，安排了材料采买工作，安排跟进了今天的成片产出工作", "telegram")

    report_data = tmp_path / "daily" / "work_report.jsonl"
    text = report_data.read_text(encoding="utf-8")
    assert "沟通外部拍摄需求" in text
    assert "安排材料采买工作" in text
    assert "跟进今日成片产出工作" in text
