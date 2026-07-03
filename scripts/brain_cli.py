#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, date
from io import StringIO
from pathlib import Path
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
try:
    TZ = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def now_dt() -> datetime:
    return datetime.now(TZ)


def iso_now() -> str:
    return now_dt().isoformat(timespec="seconds")


def today() -> str:
    return now_dt().strftime("%Y-%m-%d")


def month() -> str:
    return now_dt().strftime("%Y-%m")


def slugify(text: str, max_len: int = 60) -> str:
    text = text.strip().lower()
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = text.strip("-")
    if not text:
        text = now_dt().strftime("note-%Y%m%d-%H%M%S")
    return text[:max_len].strip("-") or "note"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def ensure_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def append_log(event: str, files: list[Path] | None = None) -> None:
    files = files or []
    rels = ", ".join(rel(p) for p in files if p.exists())
    append(ROOT / "log.md", f"- {iso_now()} — {event}" + (f" — files: {rels}" if rels else "") + "\n")


def raw_capture(text: str, source: str) -> Path:
    path = ROOT / "raw" / source / f"{today()}.jsonl"
    record = {"timestamp": iso_now(), "source": source, "text": text, "status": "captured"}
    append(path, json.dumps(record, ensure_ascii=False) + "\n")
    return path


def inbox_capture(text: str, source: str) -> Path:
    path = ROOT / "inbox" / f"{today()}.md"
    ensure_file(path, f"# Inbox {today()}\n\n")
    append(path, f"## {iso_now()} — {source}\n\n{text}\n\n")
    return path


def classify(text: str) -> list[str]:
    cats: list[str] = []
    if re.search(r"\d+(?:\.\d+)?\s*(元|块|块钱)|花了|消费|打车|早餐|午餐|晚餐|夜宵|买了", text):
        cats.append("finance")
    if re.search(r"睡|醒|早起|熬夜|身体|精神|情绪|运动|健康|腰|放松", text):
        cats.append("health")
    if re.search(r"想法|灵感|点子|观点|创意", text):
        cats.append("ideas")
    if re.search(r"项目|任务|计划|开发|产品", text):
        cats.append("projects")
    if re.search(r"钥匙|家里|车库|抽屉|鞋柜|日常|今天|昨天|明天", text):
        cats.append("life")
    if not cats:
        cats.append("life")
    return cats


def clean_expense_item(raw: str) -> str:
    item = raw.strip(" ，。；;、：:")
    item = re.sub(r"^(今天|今日|昨天|昨日|刚刚|刚才|早上|上午|中午|下午|晚上|夜里)", "", item)
    item = re.sub(r"(一共|总共|合计)?\s*(花了|花|消费|用了|支付|付了|买了)$", "", item)
    item = re.sub(r"^(买了|买|吃了|喝了)", "", item)
    item = item.strip(" ，。；;、：:")
    return item or "未命名消费"


def expense_items(text: str) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    money_context = bool(re.search(r"元|块|块钱|花了|消费|支出|买了", text))
    parts = [p.strip() for p in re.split(r"[，,。；;\n、]+", text) if p.strip()]
    for part in parts:
        # Handle amount-before-item phrases like “花了1013.08买了眼肉牛排”.
        amount_first = re.search(r"(?:花了|花|消费|支付|付了|用了)?\s*(?P<amount>\d+(?:\.\d+)?)\s*(?:元|块钱|块)?\s*(?:买了|买|购入|入手|交了|交)?\s*(?P<item>[^，,。；;\n]+)$", part)
        if amount_first and re.search(r"^(花|消费|支付|付|用|\d)", part):
            item = clean_expense_item(amount_first.group("item"))
            amount = amount_first.group("amount")
        else:
            # Prefer explicit-unit amounts, but also accept short unitless amounts in a
            # money-context message so phrases like “星巴克21” become separate rows.
            m = re.search(r"(?P<item>.*?)(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>元|块钱|块)?\s*$", part)
            if not m:
                continue
            if not m.group("unit") and not money_context:
                continue
            item = clean_expense_item(m.group("item"))
            amount = m.group("amount")
        key = (item, amount)
        if key not in seen:
            seen.add(key)
            matches.append(key)
    return matches


def expense_category(item: str) -> str:
    if any(k in item for k in ["房租", "租金", "租房", "公寓", "物业", "水电", "燃气", "宽带"]):
        return "housing"
    if any(k in item for k in ["打车", "高德", "车费", "地铁", "公交", "交通", "停车", "油费"]):
        return "commute"
    if any(k in item for k in ["牛排", "肉", "生鲜", "水果", "蔬菜", "鸡蛋", "米", "面", "粮油", "超市", "盒马", "山姆"]):
        return "grocery"
    if any(k in item for k in ["早餐", "午餐", "晚餐", "夜宵", "粥", "饭", "吃", "咖啡", "奶茶", "星巴克", "瑞幸", "麦当劳", "肯德基", "外卖"]):
        return "dining"
    return "other"


def expense_subcategory(item: str, category: str | None = None) -> str:
    category = category or expense_category(item)
    if category == "housing":
        if "房租" in item or "租金" in item or "租房" in item:
            return "房租"
        if "物业" in item:
            return "物业"
        if any(k in item for k in ["水电", "燃气", "宽带"]):
            return "水电燃气宽带"
        return "居住"
    if category == "grocery":
        if any(k in item for k in ["牛排", "肉"]):
            return "肉类/牛排"
        if any(k in item for k in ["水果", "蔬菜"]):
            return "蔬果"
        if any(k in item for k in ["米", "面", "粮油"]):
            return "米面粮油"
        return "食品生鲜"
    if category == "dining":
        if any(k in item for k in ["星巴克", "咖啡", "瑞幸"]):
            return "咖啡饮品"
        if "早餐" in item:
            return "早餐"
        if "外卖" in item:
            return "外卖"
        return "正餐"
    if category == "commute":
        if any(k in item for k in ["打车", "高德"]):
            return "打车"
        if any(k in item for k in ["地铁", "公交"]):
            return "公共交通"
        return "交通"
    return "其他"


CATEGORY_LABELS = {
    "housing": "居住",
    "grocery": "食品生鲜",
    "dining": "外食餐饮",
    "commute": "通勤交通",
    "shopping": "购物",
    "life": "日用生活",
    "entertainment": "娱乐休闲",
    "health": "健康医疗",
    "social": "人情社交",
    "other": "其他",
    # Legacy values kept for older records and tests.
    "food": "外食餐饮",
    "expense": "其他",
}

SOURCE_LABELS = {
    "telegram": "Telegram",
    "gui": "GUI",
    "manual": "手动",
}

KNOWN_MERCHANTS = ["高德", "星巴克", "瑞幸", "麦当劳", "肯德基", "绿豆粥"]


def infer_merchant(item: str) -> str:
    for keyword in KNOWN_MERCHANTS:
        if keyword in item:
            return keyword
    return ""


def expense_sync_id(date_value: str, item: str, amount: str, source: str) -> str:
    raw = f"{date_value}|{item}|{normalize_amount(amount)}|{source}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def config_text_value(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text, re.M)
    if not m:
        return None
    value = m.group(1).strip().strip('"\'')
    return value or None


def load_lark_expense_sync_config() -> dict:
    path = ROOT / "config" / "brain.yaml"
    if not path.exists():
        return {"enabled": False}
    body = path.read_text(encoding="utf-8", errors="replace")
    section_match = re.search(r"^lark_expense_sync:\s*$([\s\S]*?)(?=^\S|\Z)", body, re.M)
    if not section_match:
        return {"enabled": False}
    section = section_match.group(1)
    enabled = (config_text_value(section, "enabled") or "false").lower() in {"true", "yes", "1", "on"}
    return {
        "enabled": enabled,
        "base_token": config_text_value(section, "base_token") or "",
        "table_id": config_text_value(section, "table_id") or "",
        "identity": config_text_value(section, "identity") or "user",
    }


def lark_cli_executable() -> str:
    found = shutil.which("lark-cli")
    if found:
        return found
    candidates = [
        Path.home() / "AppData" / "Roaming" / "npm" / "lark-cli.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "lark-cli",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "lark-cli"


def expense_lark_row(date_value: str, item: str, amount: str, category: str, notes: str, source: str) -> dict:
    return {
        "同步ID": expense_sync_id(date_value, item, amount, source),
        "项目": item,
        "日期": f"{date_value} 00:00:00",
        "金额": float(amount),
        "分类": CATEGORY_LABELS.get(category, "其他"),
        "二级分类": expense_subcategory(item, category),
        "支付方式": "未知",
        "商户": infer_merchant(item),
        "备注": notes,
        "来源": SOURCE_LABELS.get(source.lower(), "外脑"),
        "月份": date_value[:7],
        "是否报销": False,
    }


def run_lark_cli(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("LARK_CLI_SUPPRESS_NOTICE", "1")
    env.setdefault("LARKSUITE_CLI_NO_UPDATE_NOTIFIER", "1")
    env.setdefault("LARKSUITE_CLI_NO_SKILLS_NOTIFIER", "1")
    return subprocess.run(
        [lark_cli_executable(), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def ensure_lark_field(config: dict, name: str, field_type: str = "text", options: list[str] | None = None) -> None:
    completed = run_lark_cli([
        "base", "+field-list",
        "--as", config["identity"],
        "--base-token", config["base_token"],
        "--table-id", config["table_id"],
        "--json",
    ])
    if completed.returncode == 0:
        try:
            data = json.loads(completed.stdout)
            fields = data.get("data", {}).get("fields", []) if isinstance(data, dict) else []
            if any(field.get("name") == name for field in fields if isinstance(field, dict)):
                return
        except json.JSONDecodeError:
            if f'"name": "{name}"' in completed.stdout or f'"name":"{name}"' in completed.stdout:
                return
    field: dict = {"name": name, "type": field_type}
    if options:
        field["multiple"] = False
        field["options"] = [{"name": option} for option in options]
    create = run_lark_cli([
        "base", "+field-create",
        "--as", config["identity"],
        "--base-token", config["base_token"],
        "--table-id", config["table_id"],
        "--json", json.dumps(field, ensure_ascii=False),
    ])
    if create.returncode != 0:
        raise RuntimeError((create.stderr or create.stdout or f"创建{name}字段失败").strip())


def ensure_lark_expense_sync_fields(config: dict) -> None:
    ensure_lark_field(config, "同步ID")
    ensure_lark_field(
        config,
        "二级分类",
        "select",
        ["房租", "物业", "水电燃气宽带", "肉类/牛排", "食品生鲜", "蔬果", "米面粮油", "咖啡饮品", "早餐", "正餐", "外卖", "打车", "公共交通", "交通", "其他"],
    )


def lark_sync_id_exists(config: dict, sync_id: str) -> bool:
    completed = run_lark_cli([
        "base", "+record-search",
        "--as", config["identity"],
        "--base-token", config["base_token"],
        "--table-id", config["table_id"],
        "--keyword", sync_id,
        "--search-field", "同步ID",
        "--field-id", "同步ID",
        "--limit", "1",
        "--format", "json",
    ])
    if completed.returncode != 0:
        return False
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False
    result = data.get("data", {}) if isinstance(data, dict) else {}
    return bool(result.get("record_id_list") or result.get("data"))


def sync_expenses_to_lark(rows: list[dict]) -> dict:
    config = load_lark_expense_sync_config()
    if not config.get("enabled"):
        return {"enabled": False, "synced": 0, "skipped": "disabled"}
    if not config.get("base_token") or not config.get("table_id"):
        return {"enabled": True, "synced": 0, "error": "missing base_token/table_id"}
    if not rows:
        return {"enabled": True, "synced": 0}
    ensure_lark_expense_sync_fields(config)
    new_rows = [row for row in rows if not lark_sync_id_exists(config, str(row.get("同步ID", "")))]
    skipped = len(rows) - len(new_rows)
    if not new_rows:
        return {"enabled": True, "synced": 0, "skipped_existing": skipped, "base_token": config["base_token"], "table_id": config["table_id"]}
    sync_fields = ["同步ID", "项目", "日期", "金额", "分类", "二级分类", "支付方式", "商户", "备注", "来源", "月份", "是否报销"]
    payload = {
        "fields": sync_fields,
        "rows": [[row.get(field) for field in sync_fields] for row in new_rows],
    }
    completed = run_lark_cli([
        "base", "+record-batch-create",
        "--as", config["identity"],
        "--base-token", config["base_token"],
        "--table-id", config["table_id"],
        "--json", json.dumps(payload, ensure_ascii=False),
    ])
    if completed.returncode != 0:
        return {"enabled": True, "synced": 0, "skipped_existing": skipped, "error": (completed.stderr or completed.stdout).strip()[:1000]}
    return {"enabled": True, "synced": len(new_rows), "skipped_existing": skipped, "base_token": config["base_token"], "table_id": config["table_id"]}


def append_expenses(text: str, source: str) -> tuple[Path | None, dict | None]:
    items = expense_items(text)
    if not items:
        return None, None
    path = ROOT / "wiki" / "finance" / "expenses" / f"{month()}.md"
    ensure_file(path, f"---\nid: expense-{month()}\ncreated: {iso_now()}\nupdated: {iso_now()}\ntype: expense\ncategory: finance\ntags: [expense, finance]\nsource: system\nconfidence: high\nprivacy: private\nrelated: []\n---\n\n# {month()} Expenses\n\n| Date | Item | Amount | Category | Notes | Source |\n|---|---:|---:|---|---|---|\n")
    lark_rows: list[dict] = []
    date_value = today()
    for item, amount in items:
        category = expense_category(item)
        notes = ""
        append(path, f"| {date_value} | {item} | {amount} | {category} | {notes} | {source} |\n")
        lark_rows.append(expense_lark_row(date_value, item, amount, category, notes, source))
    sync_result = sync_expenses_to_lark(lark_rows) if not is_test_source(source) else {"enabled": False, "synced": 0, "skipped": "test_source"}
    return path, sync_result


def append_life(text: str, source: str) -> Path:
    path = ROOT / "wiki" / "life" / "daily" / f"{today()}.md"
    ensure_file(path, f"---\nid: daily-{today()}\ncreated: {iso_now()}\nupdated: {iso_now()}\ntype: daily\ncategory: life\ntags: [daily, life]\nsource: system\nconfidence: high\nprivacy: private\nrelated: []\n---\n\n# {today()} Daily Note\n\n## Captures\n\n")
    append(path, f"- {iso_now()} ({source}) {text}\n")
    return path


def append_health(text: str, source: str) -> Path:
    if re.search(r"睡|醒|早起|熬夜", text):
        path = ROOT / "wiki" / "health" / "sleep.md"
        ensure_file(path, "# Sleep Log\n\n| Date | Bedtime | Sleep Time | Wake Time | Quality | Body Feeling | Energy | Notes | Source |\n|---|---|---|---|---|---|---|---|---|\n")
        append(path, f"| {today()} |  |  |  |  |  |  | {text.replace('|','/')} | {source} |\n")
        return path
    path = ROOT / "wiki" / "health" / "body.md"
    append(path, f"\n- {iso_now()} ({source}) {text}\n")
    return path


def append_idea(text: str, source: str) -> Path:
    path = ROOT / "wiki" / "ideas" / "captures" / f"{month()}.md"
    ensure_file(path, f"---\nid: ideas-{month()}\ncreated: {iso_now()}\nupdated: {iso_now()}\ntype: idea\ncategory: ideas\ntags: [idea]\nsource: system\nconfidence: high\nprivacy: private\nrelated: []\n---\n\n# {month()} Ideas\n\n")
    append(path, f"- {iso_now()} ({source}) {text}\n")
    return path


def is_work_report_capture(text: str) -> bool:
    if re.search(r"日报|今日复盘|明日安排|工作安排", text):
        return True
    work_terms = ["早会", "例会", "复盘", "安排", "跟进", "沟通", "对接", "整理", "审核", "投放", "成片", "拍摄", "素材", "KOC", "BD", "直客", "卡审"]
    return "工作" in text and any(term in text for term in work_terms)


def normalize_work_summary(segment: str) -> str:
    text = segment.strip(" ，。；;、：:")
    text = re.sub(r"^(外脑[，,:：]?\s*)?(记一下|记录一下|帮我记一下)?", "", text).strip(" ，。；;、：:")
    text = re.sub(r"^(我)?(今天|今日|早上|上午|下午|晚上)?(的)?工作安排", "", text).strip(" ，。；;、：:")
    text = re.sub(r"^(我)?(今天|今日|早上|上午|下午|晚上)", "", text).strip(" ，。；;、：:")
    text = text.replace("koc", "KOC").replace("bd", "BD").replace("live", "LIVE")
    text = text.replace("沟通了", "沟通").replace("复盘了", "复盘").replace("安排了", "安排").replace("跟进了", "跟进").replace("整理了", "整理").replace("审核了", "审核").replace("投放了", "投放")
    text = text.replace("安排跟进今天的", "跟进今日").replace("安排跟进了今天的", "跟进今日")
    text = text.replace("安排跟进", "跟进")
    text = text.replace("材料采买", "材料采买")
    text = re.sub(r"以及", "并", text)
    text = re.sub(r"\s+", "", text)
    text = text.strip(" ，。；;、：:")
    return text


def work_report_record_id(record_date: str, summary: str) -> str:
    return f"{record_date}-{now_dt().strftime('%H%M%S')}-review-{slugify(summary, 32)}"


def append_work_report_from_capture(text: str, source: str) -> Path | None:
    if not is_work_report_capture(text):
        return None
    path = ROOT / "daily" / "work_report.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record_date = today()
    source_text = text
    summaries: list[str] = []

    if "早会" in text and "复盘" in text and "安排" in text:
        summaries.append("早会复盘团队进度并安排今日工作")

    current_text = re.split(r"明天安排是|明日安排|明天的安排是|明天要", text, maxsplit=1)[0]
    for segment in re.split(r"[，,。；;\n]+", current_text):
        summary = normalize_work_summary(segment)
        if not summary or summary in {"我", "今天", "今日", "工作", "安排"}:
            continue
        if len(summary) < 4:
            continue
        if not any(term in summary for term in ["早会", "例会", "复盘", "安排", "跟进", "沟通", "对接", "整理", "审核", "投放", "成片", "拍摄", "素材", "KOC", "BD", "直客", "卡审", "采买"]):
            continue
        if "工作安排" == summary:
            continue
        summaries.append(summary)

    deduped: list[str] = []
    seen: set[str] = set()
    for summary in summaries:
        if summary not in seen:
            seen.add(summary)
            deduped.append(summary)
    if not deduped:
        return None

    existing_keys: set[tuple[str, str, str]] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            existing_keys.add((item.get("date", ""), item.get("type", ""), item.get("summary", "")))

    with path.open("a", encoding="utf-8") as f:
        for summary in deduped:
            key = (record_date, "review", summary)
            if key in existing_keys:
                continue
            record = {
                "id": work_report_record_id(record_date, summary),
                "created_at": iso_now(),
                "date": record_date,
                "type": "review",
                "title": summary,
                "summary": summary,
                "details": summary,
                "source_text": source_text,
                "project": "",
                "status": "done",
                "tags": ["日报"],
            }
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


TEST_SOURCES = {"verify", "e2e", "pytest", "test"}


def is_test_source(source: str) -> bool:
    return source.strip().lower() in TEST_SOURCES


def capture(text: str, source: str = "telegram") -> dict:
    changed: list[Path] = []
    raw = raw_capture(text, source); changed.append(raw)
    cats = classify(text)
    if is_test_source(source):
        append_log(f"test capture from {source}: {text[:80]}", changed)
        return {"ok": True, "categories": cats, "files": [rel(p) for p in changed], "test_source": True}
    inbox = inbox_capture(text, source); changed.append(inbox)
    work_report_path = append_work_report_from_capture(text, source)
    if work_report_path:
        changed.append(work_report_path)
    sync_results: list[dict] = []
    if "finance" in cats:
        p, sync_result = append_expenses(text, source)
        if p: changed.append(p)
        if sync_result: sync_results.append(sync_result)
    if "health" in cats:
        changed.append(append_health(text, source))
    if "ideas" in cats:
        changed.append(append_idea(text, source))
    if "life" in cats or not any(c in cats for c in ["finance", "health", "ideas"]):
        changed.append(append_life(text, source))
    if sync_results:
        for sync_result in sync_results:
            if sync_result.get("error"):
                append_log(f"lark expense sync failed: {sync_result['error']}", changed)
            elif sync_result.get("synced"):
                append_log(f"lark expense sync: {sync_result['synced']} rows", changed)
    append_log(f"capture from {source}: {text[:80]}", changed)
    result = {"ok": True, "categories": cats, "files": [rel(p) for p in changed], "test_source": False}
    if sync_results:
        result["lark_expense_sync"] = sync_results
    return result


def paths(note_type: str, date: str | None = None, title: str | None = None) -> dict:
    date = date or today()
    yyyy_mm = date[:7]
    if note_type == "expense":
        p = ROOT / "wiki" / "finance" / "expenses" / f"{yyyy_mm}.md"
    elif note_type == "daily":
        p = ROOT / "wiki" / "life" / "daily" / f"{date}.md"
    elif note_type == "article":
        p = ROOT / "wiki" / "articles" / "sources" / f"{date}-{slugify(title or 'article')}.md"
    else:
        p = ROOT / "inbox" / f"{date}.md"
    return {"path": rel(p)}


def parse_expense_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or "---" in line or "Date" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        try:
            amount = float(cells[2])
        except ValueError:
            continue
        rows.append({"date": cells[0], "item": cells[1], "amount": amount, "category": cells[3], "notes": cells[4], "source": cells[5], "file": rel(path)})
    return rows


def normalize_amount(value: str) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def parse_correction_pair(text: str) -> tuple[str, str] | None:
    patterns = [
        r"不是\s*([^，。,；;]+?)\s*(?:，|,)?\s*(?:是|而是|改成|应为|应该是)\s*([^，。,；;]+)",
        r"把\s*([^，。,；;]+?)\s*(?:改成|改为|修正为)\s*([^，。,；;]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            old = m.group(1).strip()
            new = m.group(2).strip()
            if old and new:
                return old, new
    return None


def amount_from_text(value: str) -> str | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块|块钱)?", value)
    if not m:
        return None
    return normalize_amount(m.group(1))


def correction_keywords(text: str, old: str, new: str) -> list[str]:
    cleaned = text
    for part in [old, new, "今天", "昨天", "刚才", "那条", "记录", "费用", "金额"]:
        cleaned = cleaned.replace(part, " ")
    cleaned = re.sub(r"不是|而是|应该是|应为|改成|改为|修正为|是|元|块钱|块|，|。|,|;|；|：|:", " ", cleaned)
    return [t for t in re.split(r"\s+", cleaned.strip()) if len(t) >= 2]


def find_expense_amount_candidates(old_amount: str, keywords: list[str]) -> list[dict]:
    candidates: list[dict] = []
    for path in (ROOT / "wiki" / "finance" / "expenses").glob("*.md"):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines):
            if not line.startswith("|") or "---" in line or "Date" in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6:
                continue
            if normalize_amount(cells[2]) != old_amount:
                continue
            haystack = f"{cells[0]} {cells[1]} {cells[3]} {cells[4]} {cells[5]}"
            score = sum(1 for kw in keywords if kw in haystack)
            candidates.append({
                "path": path,
                "line_index": idx,
                "line": line,
                "cells": cells,
                "score": score,
            })
    if keywords:
        best_score = max((c["score"] for c in candidates), default=0)
        if best_score > 0:
            candidates = [c for c in candidates if c["score"] == best_score]
    return candidates


def apply_expense_amount_correction(candidate: dict, new_amount: str, instruction: str) -> dict:
    path: Path = candidate["path"]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cells = list(candidate["cells"])
    old_amount = cells[2]
    cells[2] = new_amount
    new_line = "| " + " | ".join(cells) + " |"
    lines[candidate["line_index"]] = new_line
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    append_log(f"correction: {instruction} ({old_amount} -> {new_amount})", [path])
    return {
        "ok": True,
        "status": "corrected",
        "type": "expense_amount",
        "old": normalize_amount(old_amount),
        "new": normalize_amount(new_amount),
        "files": [rel(path)],
        "changes": [{"file": rel(path), "old": old_amount, "new": new_amount, "line": new_line}],
    }


def markdown_text_files_for_correction() -> list[Path]:
    roots = [ROOT / "inbox", ROOT / "wiki" / "life", ROOT / "wiki" / "health", ROOT / "wiki" / "ideas", ROOT / "wiki" / "projects"]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(p for p in root.rglob("*.md") if p.is_file())
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def correct_text_occurrence(old: str, new: str, instruction: str) -> dict:
    candidates: list[Path] = []
    for path in markdown_text_files_for_correction():
        body = path.read_text(encoding="utf-8", errors="replace")
        if old in body:
            candidates.append(path)
    if not candidates:
        return {"ok": False, "status": "not_found", "message": "没有找到可修正的匹配记录。"}
    if len(candidates) > 1:
        return {"ok": False, "status": "ambiguous", "message": "找到多条可能记录，需要更具体说明。", "candidates": [rel(p) for p in candidates[:10]]}
    path = candidates[0]
    body = path.read_text(encoding="utf-8", errors="replace")
    path.write_text(body.replace(old, new, 1), encoding="utf-8")
    append_log(f"correction: {instruction} ({old} -> {new})", [path])
    return {
        "ok": True,
        "status": "corrected",
        "type": "text",
        "old": old,
        "new": new,
        "files": [rel(path)],
        "changes": [{"file": rel(path), "old": old, "new": new}],
    }


def correct(text: str) -> dict:
    pair = parse_correction_pair(text)
    if not pair:
        return {"ok": False, "status": "unsupported", "message": "暂时只支持“不是A，是B”或“把A改成B”格式。"}
    old, new = pair
    old_amount = amount_from_text(old)
    new_amount = amount_from_text(new)
    if old_amount is not None and new_amount is not None:
        candidates = find_expense_amount_candidates(old_amount, correction_keywords(text, old, new))
        if not candidates:
            return {"ok": False, "status": "not_found", "message": "没有找到对应金额记录。", "old": old_amount, "new": new_amount}
        if len(candidates) > 1:
            return {
                "ok": False,
                "status": "ambiguous",
                "message": "找到多条同金额记录，需要补充项目名称。",
                "old": old_amount,
                "new": new_amount,
                "candidates": [{"file": rel(c["path"]), "line": c["line"]} for c in candidates[:10]],
            }
        return apply_expense_amount_correction(candidates[0], new_amount, text)
    return correct_text_occurrence(old, new, text)


def query_expenses(text: str, target_month: str | None = None) -> dict:
    target_month = target_month or month()
    path = ROOT / "wiki" / "finance" / "expenses" / f"{target_month}.md"
    all_rows = parse_expense_rows(path)
    excluded_rows = [r for r in all_rows if is_test_source(r.get("source", ""))]
    rows = [r for r in all_rows if not is_test_source(r.get("source", ""))]
    if not rows:
        answer = f"{target_month} 暂无真实消费记录。"
        if excluded_rows:
            answer += f"已排除 {len(excluded_rows)} 条测试/验证记录。"
        return {"ok": True, "type": "finance", "answer": answer, "files": [rel(path)], "excluded_test_rows": len(excluded_rows), "rows": []}
    total = sum(r["amount"] for r in rows)
    by_cat: dict[str, float] = defaultdict(float)
    by_item: list[dict] = []
    for r in rows:
        by_cat[r["category"]] += r["amount"]
        by_item.append(r)
    by_item.sort(key=lambda r: r["amount"], reverse=True)
    lines = [f"{target_month} 已记录真实消费合计 {total:g} 元。", "", "按类别："]
    for cat, amt in sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"- {cat}: {amt:g} 元")
    lines.append("")
    lines.append("较大/最近条目：")
    for r in by_item[:8]:
        lines.append(f"- {r['date']} {r['item']}：{r['amount']:g} 元（{r['category']}）")
    if excluded_rows:
        lines.append("")
        lines.append(f"已排除 {len(excluded_rows)} 条测试/验证记录（source=verify/e2e/pytest/test）。")
    lines.append("")
    lines.append(f"来源：{rel(path)}")
    return {"ok": True, "type": "finance", "month": target_month, "total": total, "by_category": dict(by_cat), "rows": rows, "excluded_test_rows": len(excluded_rows), "answer": "\n".join(lines), "files": [rel(path)]}


def filter_inbox_test_sections(body: str) -> tuple[str, int]:
    lines = body.splitlines()
    kept: list[str] = []
    skipped = 0
    current: list[str] = []
    current_source: str | None = None

    def flush() -> None:
        nonlocal skipped
        if not current:
            return
        if current_source and is_test_source(current_source):
            skipped += 1
        else:
            kept.extend(current)

    for line in lines:
        m = re.match(r"^##\s+.+?—\s*(\S+)\s*$", line)
        if m:
            flush()
            current = [line]
            current_source = m.group(1)
        elif current:
            current.append(line)
        else:
            kept.append(line)
    flush()
    return "\n".join(kept).strip() + "\n", skipped


def filter_daily_test_lines(body: str) -> tuple[str, int]:
    kept: list[str] = []
    skipped = 0
    for line in body.splitlines():
        m = re.search(r"\(([^)]+)\)", line)
        if m and is_test_source(m.group(1)):
            skipped += 1
            continue
        kept.append(line)
    return "\n".join(kept).strip() + "\n", skipped


def query_today() -> dict:
    date = today()
    files = [ROOT / "inbox" / f"{date}.md", ROOT / "wiki" / "life" / "daily" / f"{date}.md"]
    parts = []
    used = []
    excluded = 0
    for p in files:
        if p.exists():
            used.append(rel(p))
            body = p.read_text(encoding="utf-8", errors="replace")
            if rel(p).startswith("inbox/"):
                body, count = filter_inbox_test_sections(body)
            else:
                body, count = filter_daily_test_lines(body)
            excluded += count
            parts.append(f"## {rel(p)}\n" + body[-3000:])
    if not parts:
        answer = f"今天（{date}）还没有记录。"
    else:
        answer = f"今天（{date}）的真实记录来源：{', '.join(used)}\n\n" + "\n\n".join(parts)
        if excluded:
            answer += f"\n\n已排除 {excluded} 条测试/验证记录（source=verify/e2e/pytest/test）。"
    return {"ok": True, "type": "today", "answer": answer, "files": used, "excluded_test_entries": excluded}


def resolve_report_date(text: str) -> str | None:
    base = now_dt().date()
    if re.search(r"前天|前日", text):
        return (base - timedelta(days=2)).isoformat()
    if re.search(r"昨天|昨日", text):
        return (base - timedelta(days=1)).isoformat()
    if re.search(r"今天|今日", text):
        return base.isoformat()
    if re.search(r"明天|明日", text):
        return (base + timedelta(days=1)).isoformat()
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d{1,2})[./月](\d{1,2})日?", text)
    if m:
        return f"{base.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def query_work_daily_report(text: str) -> dict | None:
    if not re.search(r"日报|工作日报|今日复盘|明日安排", text):
        return None
    report_date = resolve_report_date(text) or today()
    path = ROOT / "daily" / "reports" / f"{report_date}.md"
    if path.exists():
        body = path.read_text(encoding="utf-8", errors="replace").strip()
        return {"ok": True, "type": "work_daily_report", "date": report_date, "answer": body, "files": [rel(path)], "persisted": True}

    script = ROOT / "scripts" / "work_report.py"
    if script.exists():
        plan_day = (date.fromisoformat(report_date) + timedelta(days=1)).isoformat()
        completed = subprocess.run(
            [sys.executable, str(script), "--review-day", report_date, "--plan-day", plan_day],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0 and path.exists():
            body = path.read_text(encoding="utf-8", errors="replace").strip()
            return {"ok": True, "type": "work_daily_report", "date": report_date, "answer": body, "files": [rel(path)], "persisted": True, "generated": True}
        message = completed.stderr.strip() or completed.stdout.strip() or "日报生成脚本执行失败。"
        return {"ok": False, "type": "work_daily_report", "date": report_date, "answer": f"没有找到 {report_date} 的日报，且自动生成失败：{message}", "files": []}

    return {"ok": True, "type": "work_daily_report", "date": report_date, "answer": f"没有找到 {report_date} 的成品日报。", "files": []}


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + 4 :].lstrip()
    return text


def md_title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", strip_frontmatter(text), re.M)
    return m.group(1).strip() if m else fallback


def md_section(text: str, heading: str) -> str:
    body = strip_frontmatter(text)
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", body[start:], re.M)
    end = start + nxt.start() if nxt else len(body)
    return body[start:end].strip()


def normalize_query_token(text: str) -> str:
    return re.sub(r"[\s\-_]+", "", text.strip().lower())


def frontmatter_aliases(text: str) -> list[str]:
    aliases: list[str] = []
    for match in re.finditer(r"^(?:aliases|Aliases):\s*(.+)$", text, re.M):
        raw = match.group(1).strip()
        if raw.startswith("[") and raw.endswith("]"):
            aliases.extend(part.strip().strip('"\'') for part in raw[1:-1].split(","))
        elif raw:
            aliases.append(raw)
    return [a for a in aliases if a]


def topic_query_terms(text: str) -> list[str]:
    cleaned = re.sub(r"[？?，。,.;；：:]", " ", text)
    stop = {"最近", "关于", "一下", "看看", "查询", "精确", "主题", "资料", "记录", "什么", "有哪些", "总结", "给我"}
    return [term for term in re.split(r"\s+", cleaned) if len(term.strip()) >= 2 and term.strip() not in stop]


def topic_section_filter(query: str) -> str | None:
    section_aliases = [
        ("Core Claims", ["核心观点", "观点", "结论", "主张"]),
        ("Methodology", ["方法论", "方法", "打法", "步骤"]),
        ("How To Use", ["怎么做", "怎么用", "如何用", "使用方法", "操作", "操作路径"]),
        ("When To Use", ["什么时候用", "何时用", "适用时机"]),
        ("Applicable Scenarios", ["适用场景", "场景", "适合"]),
        ("Metrics", ["指标", "数据", "看什么", "衡量", "roi", "自然流"]),
        ("Official Screenshots", ["图片", "截图", "界面", "页面"]),
        ("Cases", ["案例", "品牌", "例子"]),
        ("Ezra Implications", ["启发", "我的业务", "对我", "ezra", "主播"]),
        ("Linked Official Docs", ["官方文档", "官方", "文档"]),
        ("Linked Articles", ["文章", "来源", "链接"]),
    ]
    lowered = query.lower()
    for section, aliases in section_aliases:
        if any(alias.lower() in lowered for alias in aliases):
            return section
    return None


def topic_file_candidates(query: str) -> list[tuple[int, Path, str]]:
    topic_dir = ROOT / "wiki" / "topics"
    if not topic_dir.exists():
        return []
    terms = topic_query_terms(query)
    normalized_terms = [normalize_query_token(term) for term in terms]
    candidates: list[tuple[int, Path, str]] = []
    for path in topic_dir.rglob("*.md"):
        body = path.read_text(encoding="utf-8", errors="replace")
        title = md_title(body, path.stem)
        aliases = [title, path.stem, *frontmatter_aliases(body)]
        alias_norms = [normalize_query_token(a) for a in aliases]
        score = 0
        for term, norm in zip(terms, normalized_terms):
            if any(norm and (norm == alias or norm in alias or alias in norm) for alias in alias_norms):
                score += 10
            elif term in body:
                score += 2
        if score:
            candidates.append((score, path, title))
    return sorted(candidates, key=lambda item: (-item[0], item[1].name))


def format_topic_answer(title: str, body: str, *, section_filter: str | None = None) -> str:
    preferred_sections = ["Core Claims", "What It Is", "When To Use", "How To Use", "Methodology", "Applicable Scenarios", "Key Metrics / Signals", "Metrics", "Official Screenshots", "Cases", "Ezra Implications", "Linked Official Docs", "Linked Articles"]
    if section_filter:
        content = md_section(body, section_filter)
        if not content and section_filter == "Metrics":
            content = md_section(body, "Key Metrics / Signals")
        if not content:
            content = "这个主题页里暂时没有这个小节。"
        return f"## {title} — {section_filter}\n\n{content}".strip()
    parts = [f"## {title}"]
    scope = md_section(body, "Scope")
    if scope:
        parts.append("### Scope\n" + scope)
    for section in preferred_sections:
        content = md_section(body, section)
        if content:
            parts.append(f"### {section}\n{content}")
    return "\n\n".join(parts).strip()


def query_topic(text: str) -> dict | None:
    candidates = topic_file_candidates(text)
    if not candidates:
        return None
    score, path, title = candidates[0]
    if len(candidates) > 1 and score == candidates[1][0] and score < 10:
        return None
    body = path.read_text(encoding="utf-8", errors="replace")
    section = topic_section_filter(text)
    if section and not md_section(body, section):
        if not (section == "Metrics" and md_section(body, "Key Metrics / Signals")):
            return None
    answer = format_topic_answer(title, body, section_filter=section)
    answer += f"\n\n来源：{rel(path)}"
    return {"ok": True, "type": "topic", "topic": {"title": title, "score": score, "section_filter": section}, "answer": answer, "files": [rel(path)]}


def candidate_score(query: str, text: str) -> int:
    terms = topic_query_terms(query)
    q_norm = normalize_query_token(query)
    t_norm = normalize_query_token(text)
    score = 0
    for term in terms:
        norm = normalize_query_token(term)
        if not norm:
            continue
        if norm in t_norm or t_norm in norm:
            score += 8
        elif term in text:
            score += 4
    for i in range(max(0, len(q_norm) - 1)):
        if q_norm[i:i + 2] in t_norm:
            score += 1
    return score


def collect_query_candidates(text: str, limit: int = 6) -> list[dict]:
    candidates: list[dict] = []
    for path in (ROOT / "wiki" / "topics").rglob("*.md"):
        body = path.read_text(encoding="utf-8", errors="replace")
        title = md_title(body, path.stem)
        aliases = " ".join([title, path.stem, *frontmatter_aliases(body)])
        score = candidate_score(text, aliases + "\n" + body[:1000])
        if score:
            candidates.append({"file": rel(path), "title": title, "kind": "topic", "score": score})
    for path in (ROOT / "wiki" / "articles" / "sources").glob("*.md"):
        body = path.read_text(encoding="utf-8", errors="replace")
        title = md_title(body, path.stem)
        score = candidate_score(text, title + "\n" + path.name + "\n" + body[:1000])
        if score:
            candidates.append({"file": rel(path), "title": title, "kind": "article", "score": score})
    for path in (ROOT / "wiki" / "life" / "daily").glob("*.md"):
        body = path.read_text(encoding="utf-8", errors="replace")
        score = candidate_score(text, path.name + "\n" + body[:1000])
        if score:
            candidates.append({"file": rel(path), "title": path.stem, "kind": "daily", "score": score})
    candidates.sort(key=lambda item: (-item["score"], item["file"]))
    return candidates[:limit]


def candidate_answer(text: str, candidates: list[dict]) -> dict:
    if not candidates:
        return {"ok": True, "type": "candidates", "answer": "没有找到精确结果，也没有找到明显相近的主题/文章。", "matches": [], "files": []}
    lines = ["没有找到精确结果。", "", "你可能要找："]
    kind_label = {"topic": "主题", "article": "文章", "daily": "记录"}
    for item in candidates:
        lines.append(f"- {kind_label.get(item['kind'], item['kind'])}：{item['title']} — `{item['file']}`")
    return {"ok": True, "type": "candidates", "answer": "\n".join(lines), "matches": candidates, "files": [item["file"] for item in candidates]}


def parse_query_time_filter(text: str) -> dict | None:
    if re.search(r"最近\s*7\s*天|近\s*7\s*天|一周|最近一周", text):
        return {"kind": "recent_days", "days": 7}
    if re.search(r"最近\s*30\s*天|近\s*30\s*天|一个月|最近一月", text):
        return {"kind": "recent_days", "days": 30}
    if re.search(r"本月|这个月", text):
        return {"kind": "month", "month": month()}
    if re.search(r"今年", text):
        return {"kind": "year", "year": today()[:4]}
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if m:
        return {"kind": "date", "date": m.group(1)}
    m = re.search(r"(20\d{2}-\d{2})", text)
    if m:
        return {"kind": "month", "month": m.group(1)}
    return None


def detect_source_type(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"行动建议|可落地|启发|对我|我的业务|应用", text):
        return "action_insights"
    if re.search(r"文章|来源|链接|原文|出处", text):
        return "articles"
    if re.search(r"日记|日报|记录|inbox|daily", lowered):
        return "daily"
    return None


def article_date(path: Path, body: str) -> date | None:
    m = re.search(r"^created:\s*(20\d{2}-\d{2}-\d{2})", body, re.M)
    if m:
        return parse_date(m.group(1))
    m = re.match(r"(20\d{2}-\d{2}-\d{2})", path.name)
    if m:
        return parse_date(m.group(1))
    return None


def matches_time_filter(value: date | None, time_filter: dict | None) -> bool:
    if not time_filter:
        return True
    if not value:
        return False
    if time_filter["kind"] == "recent_days":
        cutoff = now_dt().date() - timedelta(days=int(time_filter["days"]))
        return cutoff <= value <= now_dt().date()
    if time_filter["kind"] == "date":
        return value.isoformat() == time_filter["date"]
    if time_filter["kind"] == "month":
        return value.isoformat().startswith(time_filter["month"])
    if time_filter["kind"] == "year":
        return value.isoformat().startswith(time_filter["year"])
    return True


def precise_query_terms(text: str) -> list[str]:
    cleaned = re.sub(r"最近\s*\d+\s*天|近\s*\d+\s*天|最近一周|一周|最近一月|一个月|本月|这个月|今年", " ", text)
    cleaned = re.sub(r"文章|来源|链接|原文|出处|行动建议|可落地|启发|对我|我的业务|应用|日记|日报|记录", " ", cleaned)
    return topic_query_terms(cleaned)


def query_precise_source(text: str) -> dict | None:
    source_type = detect_source_type(text)
    time_filter = parse_query_time_filter(text)
    if not source_type and not time_filter:
        return None
    terms = precise_query_terms(text)
    if source_type in {"articles", "action_insights"}:
        files = sorted((ROOT / "wiki" / "articles" / "sources").glob("*.md"), key=lambda p: p.name, reverse=True)
    elif source_type == "daily":
        files = sorted((ROOT / "wiki" / "life" / "daily").glob("*.md"), key=lambda p: p.name, reverse=True)
    else:
        files = sorted((ROOT / "wiki" / "articles" / "sources").glob("*.md"), key=lambda p: p.name, reverse=True)
        source_type = "articles"
    matches: list[dict] = []
    for path in files:
        body = path.read_text(encoding="utf-8", errors="replace")
        dt = article_date(path, body)
        if not matches_time_filter(dt, time_filter):
            continue
        haystack = body + "\n" + path.name
        score = sum(1 for term in terms if term in haystack)
        if terms and score == 0:
            continue
        title = md_title(body, path.stem)
        if source_type == "action_insights":
            content = md_section(body, "Actionable Insights for Ezra") or md_section(body, "Action Ideas")
            if not content:
                continue
        else:
            content = md_section(body, "Executive Summary") or md_section(body, "Key Insights") or strip_frontmatter(body)[:500]
        matches.append({"file": rel(path), "title": title, "date": dt.isoformat() if dt else "", "score": score, "content": content.strip()})
    matches.sort(key=lambda m: (m["date"], m["score"]), reverse=True)
    if not matches:
        return {"ok": True, "type": "precise_source", "source_type": source_type, "time_filter": time_filter, "answer": "没有找到符合时间/来源类型条件的精确记录。", "matches": [], "files": []}
    heading = {"articles": "相关文章", "action_insights": "行动建议", "daily": "日常记录"}.get(source_type, source_type)
    filter_text = ""
    if time_filter:
        if time_filter["kind"] == "recent_days":
            filter_text = f"最近 {time_filter['days']} 天"
        elif time_filter["kind"] == "month":
            filter_text = time_filter["month"]
        elif time_filter["kind"] == "year":
            filter_text = time_filter["year"]
        elif time_filter["kind"] == "date":
            filter_text = time_filter["date"]
    lines = [f"## {filter_text + ' ' if filter_text else ''}{heading}".strip()]
    for item in matches[:8]:
        date_part = f"{item['date']} " if item["date"] else ""
        lines.append(f"- {date_part}[{item['title']}]({item['file']})")
        for line in item["content"].splitlines()[:4]:
            if line.strip():
                lines.append(f"  {line.strip()}")
    files_out = [m["file"] for m in matches[:8]]
    lines.append("")
    lines.append("来源：")
    lines.extend(f"- {f}" for f in files_out)
    return {"ok": True, "type": "precise_source", "source_type": source_type, "time_filter": time_filter, "answer": "\n".join(lines), "matches": matches[:8], "files": files_out}


def query_notes(text: str) -> dict:
    work_report = query_work_daily_report(text)
    if work_report:
        return work_report
    if re.search(r"开销|消费|花了|多少钱|支出|吃饭|早餐|午餐|晚餐|打车", text):
        m = re.search(r"(20\d{2}-\d{2})", text)
        return query_expenses(text, m.group(1) if m else None)
    if re.search(r"今天|今日", text):
        return query_today()
    precise_source = query_precise_source(text)
    if precise_source and precise_source.get("matches"):
        return precise_source
    topic_result = query_topic(text)
    if topic_result:
        return topic_result
    candidates = collect_query_candidates(text)
    if candidates or precise_source:
        return candidate_answer(text, candidates)
    # Fallback simple full-text search over markdown file names/content snippets.
    terms = [t for t in re.split(r"\s+", re.sub(r"[？?，。,.;；：:]", " ", text)) if len(t) >= 2]
    matches = []
    for p in ROOT.rglob("*.md"):
        relp = rel(p)
        if ".git" in relp:
            continue
        body = p.read_text(encoding="utf-8", errors="replace")
        score = sum(1 for term in terms if term in body or term in relp)
        if score:
            snippet = body[:1200].replace("\n", " ")
            matches.append({"file": relp, "score": score, "snippet": snippet[:300]})
    matches.sort(key=lambda m: (-m["score"], m["file"]))
    if not matches:
        answer = "本地外脑里没有找到明显相关记录。"
    else:
        answer = "找到这些相关记录：\n" + "\n".join(f"- {m['file']} (score={m['score']})" for m in matches[:10])
    return {"ok": True, "type": "search", "answer": answer, "matches": matches[:10], "files": [m["file"] for m in matches[:10]]}


def list_md(items: object, default: str = "待整理。") -> str:
    if items is None:
        return f"- {default}"
    if isinstance(items, str):
        lines = [line.strip() for line in items.splitlines() if line.strip()]
    elif isinstance(items, list):
        lines = [str(item).strip() for item in items if str(item).strip()]
    else:
        lines = [str(items).strip()]
    if not lines:
        return f"- {default}"
    return "\n".join(f"- {line}" for line in lines)


def plain_md(value: object, default: str = "待补充。") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        return "\n".join(str(v).strip() for v in value if str(v).strip()) or default
    text = str(value).strip()
    return text or default


def content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    latin = re.findall(r"[A-Za-z0-9_]+", text)
    return len(cjk) + len(latin)


def frontmatter_scalar(value: object, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return text.replace("\n", " ").replace(": ", "：")


def concept_links(items: object) -> str:
    if not items:
        return "- 暂无概念。"
    values = [items] if isinstance(items, str) else list(items)
    lines = []
    for value in values:
        value = str(value).strip()
        if not value:
            continue
        if value.startswith("[[") and value.endswith("]]" ):
            lines.append(f"- {value}")
        else:
            lines.append(f"- [[{value}]]")
    return "\n".join(lines) or "- 暂无概念。"


def media_assets_md(items: object) -> str:
    if not items:
        return "- 无媒体素材。"
    if not isinstance(items, list):
        return list_md(items)
    lines = []
    for item in items:
        if not isinstance(item, dict):
            lines.append(f"- {item}")
            continue
        idx = item.get("index", "")
        kind = item.get("type") or item.get("tag") or "media"
        alt = str(item.get("alt") or item.get("name") or item.get("token") or "").replace("\n", " ").strip()
        if len(alt) > 220:
            alt = alt[:217] + "..."
        file = item.get("file") or ""
        token = item.get("token") or ""
        status = "downloaded" if item.get("downloaded") else "not-downloaded"
        suffix = f" — `{file}`" if file else (f" — token `{token}`" if token else "")
        lines.append(f"- {idx}. {kind} [{status}] {alt}{suffix}")
    return "\n".join(lines) or "- 无媒体素材。"


def numbered_md(items: object, default: str = "暂无后续问题。") -> str:
    if not items:
        return f"1. {default}"
    values = [items] if isinstance(items, str) else list(items)
    lines = [str(v).strip() for v in values if str(v).strip()]
    if not lines:
        return f"1. {default}"
    return "\n".join(f"{idx}. {line}" for idx, line in enumerate(lines, 1))


def load_article_payload(json_path: str | None) -> dict:
    if not json_path:
        return {}
    path = Path(json_path)
    if not path.is_absolute():
        path = ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def current_iso_week() -> tuple[int, int]:
    iso = now_dt().date().isocalendar()
    return iso.year, iso.week


def weekly_review_filename() -> str:
    year, week = current_iso_week()
    return f"{year}-W{week:02d}.md"


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def is_current_week(value: str) -> bool:
    parsed = parse_date(value)
    if not parsed:
        return False
    current = now_dt().date().isocalendar()
    other = parsed.isocalendar()
    return (other.year, other.week) == (current.year, current.week)


def weekly_expense_summary() -> tuple[str, int]:
    rows: list[dict] = []
    excluded = 0
    for path in (ROOT / "wiki" / "finance" / "expenses").glob("*.md"):
        for row in parse_expense_rows(path):
            if not is_current_week(row["date"]):
                continue
            if is_test_source(row.get("source", "")):
                excluded += 1
                continue
            rows.append(row)
    if not rows:
        text = "本周暂无真实消费记录。"
        if excluded:
            text += f"已排除 {excluded} 条测试/验证消费记录。"
        return text, excluded
    total = sum(r["amount"] for r in rows)
    by_cat: dict[str, float] = defaultdict(float)
    for row in rows:
        by_cat[row["category"]] += row["amount"]
    lines = [f"本周真实消费合计 {total:g} 元。", "", "按类别："]
    for cat, amount in sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"- {cat}: {amount:g} 元")
    lines.append("")
    lines.append("本周消费条目：")
    for row in sorted(rows, key=lambda r: (r["date"], -r["amount"])):
        lines.append(f"- {row['date']} {row['item']}：{row['amount']:g} 元（{row['category']}，{row['source']}，{row['file']}）")
    if excluded:
        lines.append("")
        lines.append(f"已排除 {excluded} 条测试/验证消费记录（source=verify/e2e/pytest/test）。")
    return "\n".join(lines), excluded


def weekly_life_summary() -> tuple[str, int, list[str]]:
    lines: list[str] = []
    files: list[str] = []
    excluded = 0
    for path in sorted((ROOT / "wiki" / "life" / "daily").glob("*.md")):
        parsed = parse_date(path.stem)
        if not parsed or not is_current_week(path.stem):
            continue
        body, count = filter_daily_test_lines(path.read_text(encoding="utf-8", errors="replace"))
        excluded += count
        useful = [line for line in body.splitlines() if line.strip().startswith("-") and not line.strip() == "---"]
        if useful:
            files.append(rel(path))
            lines.append(f"### {path.stem}")
            lines.extend(useful)
    if not lines:
        text = "本周暂无真实生活记录。"
    else:
        text = "\n".join(lines)
    if excluded:
        text += f"\n\n已排除 {excluded} 条测试/验证生活记录。"
    return text, excluded, files


def summarize_week() -> dict:
    year, week = current_iso_week()
    review_path = ROOT / "reviews" / "weekly" / weekly_review_filename()
    finance_text, finance_excluded = weekly_expense_summary()
    life_text, life_excluded, life_files = weekly_life_summary()
    sources = ["wiki/finance/expenses/*.md", *life_files]
    body = f"""# Weekly Review {year}-W{week:02d}

## Sources

{chr(10).join(f'- `{source}`' for source in sources)}

## 本周摘要

- 本周复盘由本地 Markdown 自动生成。
- 默认排除测试/验证来源：`verify`、`e2e`、`pytest`、`test`。

## 消费模式

{finance_text}

## 生活/项目记录

{life_text}

## 未闭环

- 检查本周真实记录是否足够完整；如果记录稀疏，下周优先补充工作推进、关键支出、健康/作息和想法。

## 下周建议

- 每天至少记录 1 条真实工作/生活安排。
- 消费记录尽量带具体项目和场景，便于周/月复盘归因。
- 把反复出现的想法整理成项目页或问题页。

## 3 个值得回答的问题

1. 本周哪些记录代表真实进展，而不只是系统搭建或测试？
2. 本周消费/作息/想法里，哪个模式最值得下周继续观察？
3. 如果下周只推进一个外脑改进，它应该是什么？

## 排除统计

- 已排除测试/验证消费记录：{finance_excluded} 条。
- 已排除测试/验证生活记录：{life_excluded} 条。
"""
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(body, encoding="utf-8")
    append_log("summary generated: week", [review_path])
    return {"ok": True, "scope": "week", "file": rel(review_path), "answer": f"已生成周复盘：{rel(review_path)}"}


def create_article(
    url: str,
    title: str | None = None,
    content: str | None = None,
    source: str = "web",
    payload: dict | None = None,
) -> dict:
    payload = payload or {}
    url = payload.get("url") or url or ""
    title = payload.get("title") or title or url.rstrip("/").split("/")[-1] or "article"
    content = payload.get("content") if payload.get("content") is not None else content
    source = payload.get("source") or source
    author = payload.get("author", "")
    published = payload.get("published", "")
    related = payload.get("related") or []
    extraction_status = payload.get("extraction_status") or ("complete" if content else "partial")
    extraction_method = payload.get("extraction_method") or ("manual_payload" if content else "manual_placeholder")
    extraction_notes = payload.get("extraction_notes") or ("" if content else "Only URL/metadata was provided; full article text was not extracted yet.")
    confidence = payload.get("confidence") or ("high" if extraction_status == "complete" else "medium")

    summary = payload.get("summary")
    tl_dr = payload.get("tl_dr") or payload.get("tldr")
    core_thesis = payload.get("core_thesis")
    structure = payload.get("structure")
    key_points = payload.get("key_points")
    important_details = payload.get("important_details")
    concepts = payload.get("concepts")
    actionable_insights = payload.get("actionable_insights")
    possible_applications = payload.get("possible_applications")
    critique = payload.get("critique") or payload.get("caveats")
    quotes = payload.get("quotes")
    follow_up = payload.get("follow_up_questions") or payload.get("follow_up")
    media_assets = payload.get("media_assets") or []
    media_manifest = payload.get("media_manifest") or ""
    raw_xml = payload.get("raw_xml") or ""

    slug = slugify(title)
    date = today()
    raw_path = ROOT / "raw" / "web" / f"{date}-{slug}.md"
    note_path = ROOT / "wiki" / "articles" / "sources" / f"{date}-{slug}.md"
    raw_body = content or f"URL: {url}\n\n(Article content not provided to CLI. Extraction status: {extraction_status}. Method: {extraction_method}.)\n"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw_body, encoding="utf-8")

    computed_word_count = word_count(content or "")
    computed_hash = content_hash(content or raw_body)
    if summary is None:
        summary = "待 Hermes 抓取正文后补充。" if not content else (content.strip().splitlines()[0][:240] if content.strip() else "待补充。")
    if tl_dr is None:
        tl_dr = plain_md(summary, "待补充。")

    captured_at = iso_now()
    note = f"""---
id: article-{date}-{slug}
created: {captured_at}
updated: {captured_at}
type: article
category: articles
tags: [article]
source: {frontmatter_scalar(source)}
url: {frontmatter_scalar(url)}
author: {frontmatter_scalar(author)}
published: {frontmatter_scalar(published)}
extraction_status: {frontmatter_scalar(extraction_status)}
extraction_method: {frontmatter_scalar(extraction_method)}
word_count: {computed_word_count}
content_hash: {computed_hash}
confidence: {frontmatter_scalar(confidence)}
privacy: private
related: {json.dumps(related, ensure_ascii=False)}
---

# {title}

## Metadata

- URL: {url}
- Source: {source}
- Author: {author}
- Published: {published}
- Captured: {captured_at}
- Extraction: {extraction_status} via {extraction_method}
- Extraction Notes: {extraction_notes or '无'}
- Word Count: {computed_word_count}
- Content Hash: {computed_hash}
- Media Manifest: {media_manifest or '无'}
- Raw XML: {raw_xml or '无'}
- Raw: `{rel(raw_path)}`

## Source Excerpt

{plain_md((content or raw_body)[:2000])}

## TL;DR

{plain_md(tl_dr)}

## Executive Summary

{list_md(summary)}

## Core Thesis

{plain_md(core_thesis)}

## Structure

{list_md(structure)}

## Key Points

{list_md(key_points)}

## Important Details

{list_md(important_details)}

## Media Assets

{media_assets_md(media_assets)}

## Concepts

{concept_links(concepts)}

## Actionable Insights for Ezra

{list_md(actionable_insights)}

## Possible Applications

{list_md(possible_applications)}

## Critique / Caveats

{list_md(critique)}

## Useful Quotes

{list_md(quotes, default='暂无摘录。')}

## Related Notes

{list_md(related, default='暂无关联。')}

## Follow-up Questions

{numbered_md(follow_up)}

"""
    note_path.write_text(note, encoding="utf-8")

    index_path = ROOT / "wiki" / "articles" / "index.md"
    index_line = f"- [{title}](sources/{note_path.name}) — {url} — {extraction_status}/{extraction_method}\n"
    existing = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Articles Index\n\n"
    if index_line not in existing:
        append(index_path, index_line)
    append_log(f"article captured: {title} ({extraction_status}/{extraction_method})", [raw_path, note_path, index_path])
    return {
        "ok": True,
        "title": title,
        "url": url,
        "files": [rel(raw_path), rel(note_path), "wiki/articles/index.md"],
        "extraction_status": extraction_status,
        "extraction_method": extraction_method,
        "word_count": computed_word_count,
        "content_hash": computed_hash,
    }


def summarize(scope: str) -> dict:
    if re.search(r"今天|今日|day|daily", scope, re.I):
        q = query_today()
        review_path = ROOT / "reviews" / "daily" / f"{today()}.md"
        body = f"# Daily Review {today()}\n\n## Sources\n\n" + "\n".join(f"- {f}" for f in q.get("files", [])) + "\n\n## Raw Summary Material\n\n" + q["answer"] + "\n"
    elif re.search(r"本周|这周|week|weekly", scope, re.I):
        return summarize_week()
    else:
        finance = query_expenses(scope)
        review_path = ROOT / "reviews" / "monthly" / f"{month()}.md"
        body = f"# Monthly Review {month()}\n\n## Finance\n\n{finance['answer']}\n\n## Notes\n\n待 Hermes 进一步综合 life/health/ideas。\n"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(body, encoding="utf-8")
    append_log(f"summary generated: {scope}", [review_path])
    return {"ok": True, "scope": scope, "file": rel(review_path), "answer": f"已生成总结：{rel(review_path)}"}


def questions(scope: str) -> dict:
    q = query_notes(scope)
    path = ROOT / "reviews" / "questions" / f"{today()}-{slugify(scope, 30)}.md"
    prompt = f"# Reflective Questions — {scope}\n\n## Basis\n\n{q['answer']}\n\n## Questions\n\n1. 最近这些记录里，哪个反复出现的问题最值得认真处理？\n2. 哪个消费/作息/想法模式和你的长期目标最不一致？\n3. 如果只能选择一个下周行动来改善当前状态，它应该是什么？\n\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    append_log(f"questions generated: {scope}", [path])
    return {"ok": True, "scope": scope, "file": rel(path), "answer": prompt}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Second Brain CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capture")
    p_cap.add_argument("--text", required=True)
    p_cap.add_argument("--source", default="telegram")

    p_paths = sub.add_parser("paths")
    p_paths.add_argument("--type", required=True)
    p_paths.add_argument("--date")
    p_paths.add_argument("--title")

    p_query = sub.add_parser("query")
    p_query.add_argument("--text", required=True)

    p_article = sub.add_parser("article")
    p_article.add_argument("--url", required=True)
    p_article.add_argument("--title")
    p_article.add_argument("--content")
    p_article.add_argument("--source", default="web")
    p_article.add_argument("--payload-json")

    p_summary = sub.add_parser("summary")
    p_summary.add_argument("--scope", required=True)

    p_questions = sub.add_parser("questions")
    p_questions.add_argument("--scope", required=True)

    p_correct = sub.add_parser("correction")
    p_correct.add_argument("--text", required=True)

    sub.add_parser("validate")
    sub.add_parser("rebuild-index")

    args = parser.parse_args(argv)
    if args.cmd == "capture":
        print(json.dumps(capture(args.text, args.source), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "paths":
        print(json.dumps(paths(args.type, args.date, args.title), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "query":
        print(json.dumps(query_notes(args.text), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "article":
        payload = load_article_payload(args.payload_json)
        print(json.dumps(create_article(args.url, args.title, args.content, args.source, payload), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "summary":
        print(json.dumps(summarize(args.scope), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "questions":
        print(json.dumps(questions(args.scope), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "correction":
        print(json.dumps(correct(args.text), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "validate":
        return subprocess.call([sys.executable, str(ROOT / "scripts" / "validate_brain.py")])
    if args.cmd == "rebuild-index":
        return subprocess.call([sys.executable, str(ROOT / "scripts" / "rebuild_index.py")])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
