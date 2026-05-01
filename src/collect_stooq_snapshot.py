import argparse
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SYMBOLS = {
    "spx": {"symbol": "^spx", "label": "S&P 500", "source": "https://stooq.com/q/l/?s=%5Espx&f=sd2t2ohlcv&h&e=csv"},
    "nasdaq": {"symbol": "^ndq", "label": "NASDAQ 100", "source": "https://stooq.com/q/l/?s=%5Endq&f=sd2t2ohlcv&h&e=csv"},
    "dow": {"symbol": "^dji", "label": "Dow Jones", "source": "https://stooq.com/q/l/?s=%5Edji&f=sd2t2ohlcv&h&e=csv"},
    "gold": {"symbol": "gc.f", "label": "Gold Futures", "source": "https://stooq.com/q/l/?s=gc.f&f=sd2t2ohlcv&h&e=csv"},
    "usdkrw": {"symbol": "usdkrw", "label": "USD/KRW", "source": "https://stooq.com/q/l/?s=usdkrw&f=sd2t2ohlcv&h&e=csv"},
}


def fetch_quote(symbol):
    url = "https://stooq.com/q/l/?s=" + urllib.parse.quote(symbol) + "&f=sd2t2ohlcv&h&e=csv"
    with urllib.request.urlopen(url, timeout=20) as response:
        text = response.read().decode("utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        raise RuntimeError(f"No data returned for {symbol}")
    row = rows[0]
    if row.get("Close") == "N/D":
        raise RuntimeError(f"No quote available for {symbol}")
    return {
        "date": row.get("Date"),
        "time": row.get("Time"),
        "open": float(row["Open"]) if row.get("Open") else None,
        "high": float(row["High"]) if row.get("High") else None,
        "low": float(row["Low"]) if row.get("Low") else None,
        "close": float(row["Close"]) if row.get("Close") else None,
        "volume": row.get("Volume") or None,
    }


def classify_direction(open_price, close_price):
    if open_price is None or close_price is None:
        return "flat"
    if close_price > open_price:
        return "up"
    if close_price < open_price:
        return "down"
    return "flat"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    snapshot = {
        "collected_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Seoul",
        "provider": "Stooq delayed quote CSV",
        "quotes": [],
    }
    for key, meta in SYMBOLS.items():
        quote = fetch_quote(meta["symbol"])
        open_price = quote["open"]
        close_price = quote["close"]
        open_change_pct = None
        if open_price:
            open_change_pct = ((close_price - open_price) / open_price) * 100
        snapshot["quotes"].append({
            "id": key,
            "label": meta["label"],
            "symbol": meta["symbol"],
            "source_url": meta["source"],
            "direction": "gold" if key == "gold" else classify_direction(open_price, close_price),
            "open_change_pct": round(open_change_pct, 2) if open_change_pct is not None else None,
            **quote,
        })

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
