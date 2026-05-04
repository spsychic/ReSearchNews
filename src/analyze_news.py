import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


KEYWORDS = {
    "금리": ["금리", "연준", "Fed", "FOMC", "국채", "채권"],
    "환율": ["환율", "달러", "원화", "원/달러"],
    "증시": ["증시", "나스닥", "코스피", "코스닥", "S&P", "주가"],
    "금": ["금 가격", "금값", "안전자산", "골드"],
    "부동산": ["부동산", "주택", "전세", "실거래", "대출", "분양", "재건축"],
    "정책": ["정책", "정부", "규제", "완화", "대책", "세금", "DSR"],
}


MARKET_TERMS = ["마감", "개장", "장중", "속보", "환율", "금리", "나스닥", "코스피", "코스닥", "외국인", "미국장", "뉴욕증시"]


def score_article(article):
    text = f"{article.get('title', '')} {article.get('publisher', '')}"
    hits = []
    for bucket, words in KEYWORDS.items():
        if any(word.lower() in text.lower() for word in words):
            hits.append(bucket)
    return hits


def is_recent(article, recent_hours):
    if recent_hours <= 0:
        return True
    published = article.get("published_at")
    if not published:
        return False
    try:
        published_dt = datetime.strptime(published, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Seoul"))
    except ValueError:
        return False
    return published_dt >= datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(hours=recent_hours)


def article_rank(item):
    published = item.get("published_at") or ""
    title = item.get("title", "")
    keyword_score = len(item.get("keyword_buckets", []))
    market_score = sum(1 for word in MARKET_TERMS if word.lower() in title.lower())
    priority = int(item.get("query_priority", 0))
    return (priority, market_score, keyword_score, published)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--news", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--recent-hours", type=int, default=36)
    args = parser.parse_args()

    news = json.loads(Path(args.news).read_text(encoding="utf-8"))
    raw_articles = news.get("articles", [])
    articles = [article for article in raw_articles if is_recent(article, args.recent_hours)]
    enriched = []
    buckets = Counter()
    for article in articles:
        hits = score_article(article)
        if hits:
            buckets.update(hits)
        enriched.append({**article, "keyword_buckets": hits})

    ranked = sorted(
        enriched,
        key=article_rank,
        reverse=True,
    )
    top_articles = ranked[:args.limit]
    dominant = buckets.most_common(3)

    if dominant:
        theme_text = ", ".join(f"{name}({count})" for name, count in dominant)
        interpretation = f"뉴스 키워드 기준으로는 {theme_text} 이슈가 상대적으로 많이 포착됩니다."
    else:
        interpretation = "시장 판단을 바꿀 만한 반복 키워드가 뚜렷하지 않아 신규 이슈는 공란에 가깝습니다."

    payload = {
        "analyzed_at": news.get("collected_at"),
        "provider": news.get("provider"),
        "recent_hours": args.recent_hours,
        "raw_article_count": len(raw_articles),
        "recent_article_count": len(articles),
        "dominant_buckets": [{"name": name, "count": count} for name, count in dominant],
        "interpretation": interpretation,
        "top_articles": top_articles,
        "source_urls": [article.get("source_url") for article in top_articles if article.get("source_url")],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
