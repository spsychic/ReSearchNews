import argparse
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo


RSS_URL = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"


def clean_text(value):
    return " ".join((value or "").split())


def parse_dt(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def fetch_query(query):
    url = RSS_URL.format(query=urllib.parse.quote(query))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        xml_text = response.read().decode("utf-8")
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        source = item.find("source")
        source_name = clean_text(source.text if source is not None else "")
        source_url = source.attrib.get("url") if source is not None else None
        link = clean_text(item.findtext("link"))
        items.append({
            "title": clean_text(item.findtext("title")),
            "publisher": source_name,
            "source_url": source_url or link,
            "google_news_url": link,
            "published_at": parse_dt(item.findtext("pubDate")),
        })
    return items


def dedupe_articles(groups, max_items_per_query):
    seen = set()
    articles = []
    for group in groups:
        for article in group["articles"][:max_items_per_query]:
            key = (article["title"], article["publisher"])
            if key in seen:
                continue
            seen.add(key)
            merged = dict(article)
            merged["query_id"] = group["id"]
            merged["query_label"] = group["label"]
            articles.append(merged)
    return articles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    max_items = int(config.get("max_items_per_query", 8))
    groups = []
    for query in config["queries"]:
        articles = fetch_query(query["query"])
        groups.append({
            "id": query["id"],
            "label": query["label"],
            "query": query["query"],
            "articles": articles,
        })

    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "collected_at": now,
        "timezone": "Asia/Seoul",
        "provider": "Google News RSS",
        "groups": groups,
        "articles": dedupe_articles(groups, max_items),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
