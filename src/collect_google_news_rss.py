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


def parse_sort_dt(value):
    if not value:
        return datetime.min.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Seoul"))
    except ValueError:
        return datetime.min.replace(tzinfo=ZoneInfo("Asia/Seoul"))


def build_search_query(query, recency):
    parts = [query.strip()]
    if recency:
        parts.append(recency.strip())
    return " ".join(part for part in parts if part)


def fetch_query(query, recency=None):
    search_query = build_search_query(query, recency)
    url = RSS_URL.format(query=urllib.parse.quote(search_query))
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


def normalize_title(title):
    title = clean_text(title).lower()
    for sep in (" - ", " | ", " : "):
        if sep in title:
            title = title.split(sep)[0]
    return title


def should_exclude(article, exclude_keywords):
    title = article.get("title", "").lower()
    return any(keyword.lower() in title for keyword in exclude_keywords)


def article_rank(article):
    published = parse_sort_dt(article.get("published_at"))
    priority = int(article.get("query_priority", 0))
    freshness = published.timestamp()
    title = article.get("title", "")
    market_bonus = 0
    for word in ("마감", "개장", "장중", "속보", "환율", "금리", "나스닥", "코스피", "외국인", "미국장"):
        if word.lower() in title.lower():
            market_bonus += 1
    return (priority, market_bonus, freshness)


def dedupe_articles(groups, max_items_per_query, exclude_keywords):
    seen = set()
    articles = []
    for group in groups:
        group_articles = [article for article in group["articles"] if not should_exclude(article, exclude_keywords)]
        group_articles = sorted(group_articles, key=article_rank, reverse=True)
        for article in group_articles[:max_items_per_query]:
            key = (normalize_title(article["title"]), article["publisher"])
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
    exclude_keywords = config.get("exclude_title_keywords", [])
    groups = []
    for query in config["queries"]:
        recency = query.get("recency")
        articles = fetch_query(query["query"], recency)
        priority = int(query.get("priority", 0))
        for article in articles:
            article["query_priority"] = priority
        groups.append({
            "id": query["id"],
            "label": query["label"],
            "query": query["query"],
            "recency": recency,
            "priority": priority,
            "effective_query": build_search_query(query["query"], recency),
            "articles": articles,
        })

    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "collected_at": now,
        "timezone": "Asia/Seoul",
        "provider": "Google News RSS",
        "exclude_title_keywords": exclude_keywords,
        "groups": groups,
        "articles": dedupe_articles(groups, max_items, exclude_keywords),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
