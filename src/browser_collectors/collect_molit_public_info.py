import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


MOLIT_URL = "https://www.molit.go.kr/portal.do"
RT_URL = "https://rt.molit.go.kr/"


def clean_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_policy_news(text, limit=8):
    lines = clean_lines(text)
    try:
        start = lines.index("정책뉴스")
        end = lines.index("정책뉴스 더보기", start)
    except ValueError:
        return []
    segment = lines[start + 1:end]
    items = []
    idx = 0
    while idx < len(segment):
        category = segment[idx]
        date = ""
        title = ""
        if idx + 3 < len(segment) and re.fullmatch(r"\d{1,2}", segment[idx + 1]) and re.fullmatch(r"\d{4}\.\d{2}", segment[idx + 2]):
            date = f"{segment[idx + 2]}.{int(segment[idx + 1]):02d}"
            title = segment[idx + 3]
            idx += 4
        elif idx + 2 < len(segment) and re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", segment[idx + 2]):
            title = segment[idx + 1]
            date = segment[idx + 2]
            idx += 3
        else:
            idx += 1
            continue
        if title and not any(item["title"] == title for item in items):
            items.append({"category": category, "date": date, "title": title})
        if len(items) >= limit:
            break
    return items


def extract_notices(text, limit=6):
    lines = clean_lines(text)
    try:
        start = lines.index("공지사항")
        end = lines.index("공지사항 더보기", start)
    except ValueError:
        return []
    segment = [line for line in lines[start + 1:end] if line != "새글"]
    items = []
    idx = 0
    while idx < len(segment) - 1:
        title = segment[idx]
        date = segment[idx + 1]
        if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", date):
            items.append({"date": date, "title": title})
            idx += 2
        else:
            idx += 1
        if len(items) >= limit:
            break
    return items


def extract_rt_release(text):
    lines = clean_lines(text)
    try:
        start = lines.index("보도자료")
    except ValueError:
        return {}
    segment = lines[start:start + 120]
    date = next((line for line in segment if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", line)), "")
    title = ""
    for idx, line in enumerate(segment):
        if line == date and idx + 1 < len(segment):
            title = segment[idx + 1]
            break
    facts = []
    for line in segment:
        if any(keyword in line for keyword in ("미분양", "매매거래량", "전월세 거래량", "수도권", "지방")):
            facts.append(line)
        if len(facts) >= 8:
            break
    return {"date": date, "title": title, "facts": facts}


def get_body(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    return page.title(), page.locator("body").inner_text(timeout=15000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1365, "height": 900})
        molit_title, molit_text = get_body(page, MOLIT_URL)
        rt_title, rt_text = get_body(page, RT_URL)
        browser.close()

    payload = {
        "collected_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Seoul",
        "provider": "MOLIT and RT public pages via browser",
        "molit": {
            "source_url": MOLIT_URL,
            "title": molit_title,
            "policy_news": extract_policy_news(molit_text),
            "notices": extract_notices(molit_text),
        },
        "real_trade": {
            "source_url": RT_URL,
            "title": rt_title,
            "latest_release": extract_rt_release(rt_text),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
