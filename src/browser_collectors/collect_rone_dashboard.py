import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


URL = "https://www.reb.or.kr/r-one/portal/main/indexPage.do"
SURVEY_LABELS = {
    "전국주택가격동향조사",
    "공동주택실거래가격지수",
    "오피스텔가격동향조사",
    "부동산거래현황",
    "전국지가변동률조사",
    "상업용부동산 임대동향조사",
}


def is_number(value):
    return bool(re.fullmatch(r"-?\d+(?:,\d{3})*(?:\.\d+)?", value.strip()))


def parse_dashboard(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    metrics = []
    for idx, line in enumerate(lines):
        if line not in SURVEY_LABELS:
            continue
        window = lines[idx + 1:idx + 8]
        if len(window) < 3:
            continue
        period = window[0]
        value_pos = next((pos for pos, value in enumerate(window[1:], start=1) if is_number(value)), None)
        if value_pos is None:
            continue
        descriptor = " ".join(window[1:value_pos])
        value_raw = window[value_pos]
        try:
            value = float(value_raw.replace(",", ""))
        except ValueError:
            continue
        metrics.append({
            "survey": line,
            "period": period,
            "descriptor": descriptor,
            "value": value,
            "raw_value": value_raw,
        })
    return metrics[:8]


def metric_direction(metric):
    descriptor = metric["descriptor"]
    value = metric["value"]
    if "거래" in descriptor or "호수" in descriptor or "필지" in descriptor:
        return "flat"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1365, "height": 900})
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        title = page.title()
        text = page.locator("body").inner_text(timeout=15000)
        browser.close()

    metrics = parse_dashboard(text)
    for metric in metrics:
        metric["direction"] = metric_direction(metric)

    payload = {
        "collected_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Seoul",
        "provider": "R-ONE public dashboard via browser",
        "source_url": URL,
        "title": title,
        "metrics": metrics,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
