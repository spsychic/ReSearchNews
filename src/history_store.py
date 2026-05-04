import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SLOTS = ("0600", "0700", "1600")


def infer_slot(now):
    hour = now.hour
    if hour < 7:
        return "0600"
    if hour < 16:
        return "0700"
    return "1600"


def read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_payload(payload):
    sections = payload.get("sections", [])
    by_id = {section.get("id"): section for section in sections}
    forecast_cards = payload.get("forecast_0600", {}).get("insight_cards", [])
    return {
        "generated_at": payload.get("generated_at"),
        "summary_headline": payload.get("summary", {}).get("headline"),
        "market_metrics": payload.get("summary", {}).get("metrics", []),
        "forecast_cards": forecast_cards,
        "fresh_news_status": by_id.get("fresh_news", {}).get("status"),
        "fresh_news_body": by_id.get("fresh_news", {}).get("body"),
        "us_market_body": by_id.get("us_market", {}).get("body"),
        "kr_market_body": by_id.get("kr_market", {}).get("body"),
        "gold_body": by_id.get("gold", {}).get("body"),
        "real_estate_body": by_id.get("real_estate", {}).get("body"),
        "policy_body": by_id.get("policy", {}).get("body"),
        "news_market_check": payload.get("news_market_check", {}),
    }


def update_index(index_path, entry, max_entries):
    index = read_json(index_path, {"entries": []})
    entries = index.get("entries", [])
    entries = [item for item in entries if not (
        item.get("report_date") == entry["report_date"]
        and item.get("slot") == entry["slot"]
    )]
    entries.insert(0, entry)
    index["entries"] = entries[:max_entries]
    index["updated_at"] = entry["saved_at"]
    write_json(index_path, index)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--publish-dir", default="public")
    parser.add_argument("--slot", default="auto", choices=("auto", *SLOTS))
    parser.add_argument("--max-entries", type=int, default=90)
    args = parser.parse_args()

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    slot = infer_slot(now) if args.slot == "auto" else args.slot
    report_date = now.strftime("%Y-%m-%d")

    root = Path(args.publish_dir)
    history_root = root / "history"
    daily_root = history_root / report_date / slot
    latest_root = history_root / "latest"
    daily_root.mkdir(parents=True, exist_ok=True)
    latest_root.mkdir(parents=True, exist_ok=True)

    payload_path = Path(args.payload)
    html_path = Path(args.html)
    payload = read_json(payload_path, {})

    shutil.copy2(payload_path, daily_root / "payload.json")
    shutil.copy2(html_path, daily_root / "index.html")
    shutil.copy2(payload_path, latest_root / f"{slot}.json")

    summary = {
        "report_date": report_date,
        "slot": slot,
        "saved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "payload_url": f"history/{report_date}/{slot}/payload.json",
        "html_url": f"history/{report_date}/{slot}/index.html",
        "latest_payload_url": f"history/latest/{slot}.json",
        "summary": summarize_payload(payload),
    }
    write_json(daily_root / "summary.json", summary)
    write_json(latest_root / f"{slot}_summary.json", summary)
    update_index(history_root / "index.json", summary, args.max_entries)
    print(f"saved history {report_date}/{slot}")


if __name__ == "__main__":
    main()
