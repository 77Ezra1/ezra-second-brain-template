#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(os.environ.get("HERMES_SECOND_BRAIN_ROOT", Path(__file__).resolve().parents[1]))
REPORT_PATH = ROOT / "daily" / "work_report.jsonl"


def current_date() -> date:
    override = os.environ.get("HERMES_TODAY")
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return date.today()


def resolve_day(day: str) -> str:
    today = current_date()
    if day in ("today", "今天", "今日"):
        return today.isoformat()
    if day in ("tomorrow", "明天", "明日"):
        return (today + timedelta(days=1)).isoformat()
    if day in ("yesterday", "昨天"):
        return (today - timedelta(days=1)).isoformat()
    if day in ("day_before_yesterday", "前天"):
        return (today - timedelta(days=2)).isoformat()
    return day


def load_records() -> list[dict]:
    if not REPORT_PATH.exists():
        return []
    records: list[dict] = []
    for line in REPORT_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    load_persisted_tomorrow_arrangements(records)
    return records


def load_persisted_tomorrow_arrangements(records: list[dict]) -> None:
    """Import persisted previous-day 明日安排 as same-day plan records.

    Some historical/final reports were manually edited and persisted only as
    `daily/reports/YYYY-MM-DD.md`. Include their next-day plan section so today's
    report does not miss yesterday's checklist.
    """
    reports_dir = ROOT / "daily" / "reports"
    if not reports_dir.exists():
        return
    existing = {
        (str(item.get("date") or ""), str(item.get("type") or ""), report_text(item))
        for item in records
    }
    for path in reports_dir.glob("*.md"):
        try:
            base_day = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        target_date = (base_day + timedelta(days=1)).isoformat()
        lines = path.read_text(encoding="utf-8").splitlines()
        in_plan = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if "明日安排" in stripped:
                in_plan = True
                continue
            if in_plan and "今日复盘" in stripped:
                in_plan = False
                continue
            if not in_plan:
                continue
            if not stripped[0].isdigit() or "." not in stripped:
                continue
            title = stripped.split(".", 1)[1].strip()
            if not title or title == "暂无记录":
                continue
            key = (target_date, "plan", title)
            if key in existing:
                continue
            records.append(
                {
                    "id": f"{target_date}-persisted-plan-{path.stem}-{len(records)}",
                    "created_at": path.stem,
                    "date": target_date,
                    "type": "plan",
                    "title": title,
                    "summary": title,
                    "details": f"来自 {path.name} 的明日安排：{title}",
                    "source_text": path.name,
                    "status": "pending",
                    "tags": ["日报", "明日安排", "persisted-report"],
                }
            )
            existing.add(key)
    return records


def short(text: object, limit: int = 34) -> str:
    text = "".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit]


def report_text(item: dict, limit: int = 34) -> str:
    """Return a daily-report line without losing the concrete work situation.

    `summary` is the preferred report field, but older/hand-written records may
    be overly compressed. In that case fall back to the title/details so the
    report still distinguishes object + action + context.
    """
    candidates = [
        item.get("summary"),
        item.get("title"),
        item.get("details"),
    ]
    for candidate in candidates:
        text = "".join(str(candidate or "").split())
        if text:
            return short(text, limit)
    return ""


def report_path(review_date: str) -> Path:
    return ROOT / "daily" / "reports" / f"{review_date}.md"


def save_report(review_date: str, content: str) -> Path:
    path = report_path(review_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def format_md(records: list[dict], review_day: str = "today", plan_day: str = "tomorrow") -> str:
    review_date = resolve_day(review_day)
    plan_date = resolve_day(plan_day)
    grouped: dict[tuple[str | None, str | None], list[dict]] = defaultdict(list)
    for record in records:
        grouped[(record.get("date"), record.get("type"))].append(record)

    review_items = grouped.get((review_date, "review"), []) + grouped.get((review_date, "work"), [])
    # Treat same-day plan items as report candidates too. Ezra's previous-day
    # 明日安排 are often the best checklist for today's actual work; omitting
    # them makes 今日复盘 look incomplete unless every planned item is manually
    # re-recorded as done. De-duplicate against explicit review/work records.
    seen_review_texts = {report_text(item) for item in review_items}
    for item in grouped.get((review_date, "plan"), []):
        text = report_text(item)
        if text and text not in seen_review_texts:
            review_items.append(item)
            seen_review_texts.add(text)
    plan_items = grouped.get((plan_date, "plan"), [])

    def label(iso_date: str) -> str:
        month, day = iso_date.split("-")[1:]
        return f"{int(month)}/{int(day)}"

    lines = [f"{label(review_date)} 今日复盘"]
    if review_items:
        for index, item in enumerate(review_items, 1):
            lines.append(f"{index}. {report_text(item)}")
    else:
        lines.append("1. 暂无记录")

    lines.append("")
    lines.append(f"{label(plan_date)} 明日安排")
    if plan_items:
        for index, item in enumerate(plan_items, 1):
            lines.append(f"{index}. {report_text(item)}")
    else:
        lines.append("1. 暂无记录")

    return "\n".join(lines)


def generate_report(review_day: str = "today", plan_day: str = "tomorrow", save: bool = True) -> str:
    review_date = resolve_day(review_day)
    content = format_md(load_records(), review_date, plan_day)
    if save:
        save_report(review_date, content)
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Ezra's concise work daily report.")
    parser.add_argument("--review-day", default="today")
    parser.add_argument("--plan-day", default="tomorrow")
    parser.add_argument("--no-save", action="store_true", help="Print only; do not persist daily/reports/YYYY-MM-DD.md")
    args = parser.parse_args()
    print(generate_report(args.review_day, args.plan_day, save=not args.no_save))


if __name__ == "__main__":
    main()
