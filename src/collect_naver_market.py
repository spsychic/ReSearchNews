import argparse
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


INDEXES = {
    "kospi": {"code": "KOSPI", "label": "KOSPI"},
    "kosdaq": {"code": "KOSDAQ", "label": "KOSDAQ"},
}


def extract(pattern, text):
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def to_float(value):
    if value is None:
        return None
    return float(value.replace(",", "").replace("%", "").strip())


def fetch_index(code):
    url = f"https://finance.naver.com/sise/sise_index.naver?code={code}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("euc-kr", errors="ignore")

    now_value = extract(r'id="now_value">([^<]+)</em>', html)
    change_block = extract(r'id="change_value_and_rate">(.*?)</span>\s*</div>', html)
    change_value = None
    change_pct = None
    direction_text = None
    if change_block:
        change_value = extract(r"<span>([^<]+)</span>", change_block)
        pct_match = re.search(r"([+-]?\d+(?:\.\d+)?)%", change_block)
        change_pct = float(pct_match.group(1)) if pct_match else None
        direction_text = extract(r'<span class="blind">([^<]+)</span>', change_block)

    direction = "flat"
    if change_pct is not None:
        direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
    elif direction_text and "상승" in direction_text:
        direction = "up"
    elif direction_text and "하락" in direction_text:
        direction = "down"

    return {
        "code": code,
        "source_url": url,
        "close": to_float(now_value),
        "change": to_float(change_value),
        "change_pct": change_pct,
        "direction": direction,
        "direction_text": direction_text,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    indexes = []
    for key, meta in INDEXES.items():
        row = fetch_index(meta["code"])
        row["id"] = key
        row["label"] = meta["label"]
        indexes.append(row)

    payload = {
        "collected_at": now,
        "timezone": "Asia/Seoul",
        "provider": "Naver Finance public page",
        "indexes": indexes,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
