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


SIGNAL_RULES = [
    {
        "tag": "위험선호",
        "bias": 2,
        "words": ["상승", "급등", "강세", "최고치", "신고가", "호실적", "순매수", "회복", "돌파", "랠리", "완화", "인하"],
    },
    {
        "tag": "위험회피",
        "bias": -2,
        "words": ["하락", "급락", "약세", "폭락", "조정", "불확실", "충격", "위기", "연체", "긴축", "인상", "강달러", "고금리"],
    },
    {
        "tag": "금리부담",
        "bias": -1,
        "words": ["금리 상승", "금리 인상", "인상 시사", "국채금리", "채권금리", "긴축"],
    },
    {
        "tag": "환율안정",
        "bias": 1,
        "words": ["환율 하락", "원화 강세", "원·달러 하락", "원/달러 하락", "달러 약세"],
    },
    {
        "tag": "환율부담",
        "bias": -1,
        "words": ["환율 상승", "원화 약세", "원·달러 상승", "원/달러 상승", "강달러"],
    },
    {
        "tag": "부동산회복",
        "bias": 1,
        "words": ["매수세", "거래량 증가", "미분양 감소", "상승", "회복"],
    },
    {
        "tag": "부동산부담",
        "bias": -1,
        "words": ["미분양 증가", "연체", "대출 부담", "전세사기", "하락"],
    },
]


def score_article(article):
    text = f"{article.get('title', '')} {article.get('publisher', '')}"
    hits = []
    for bucket, words in KEYWORDS.items():
        if any(word.lower() in text.lower() for word in words):
            hits.append(bucket)
    return hits


def classify_article_signal(article):
    title = article.get("title", "")
    lowered = title.lower()
    tags = []
    score = 0
    has_fx_context = any(word in lowered for word in ["환율", "원·달러", "원/달러", "달러"])
    has_real_estate_context = any(word in lowered for word in ["부동산", "주택", "전세", "미분양", "대출", "아파트", "빌라"])
    if has_fx_context and "하락" in lowered and "원화 하락" not in lowered:
        tags.append("환율안정")
        score += 2
    if has_fx_context and "상승" in lowered and "원화 상승" not in lowered:
        tags.append("환율부담")
        score -= 2
    for rule in SIGNAL_RULES:
        if rule["tag"] in ("부동산회복", "부동산부담") and not has_real_estate_context:
            continue
        if any(word.lower() in lowered for word in rule["words"]):
            if rule["tag"] == "위험회피" and has_fx_context and any(word in lowered for word in ["하락", "환율 하락", "원·달러 하락", "원/달러 하락", "달러 약세"]):
                continue
            tags.append(rule["tag"])
            score += rule["bias"]
    if score >= 2:
        stance = "호재"
    elif score <= -2:
        stance = "악재"
    elif score > 0:
        stance = "완만한 호재"
    elif score < 0:
        stance = "완만한 악재"
    else:
        stance = "중립"
    return {
        "stance": stance,
        "score": score,
        "tags": tags or ["방향 미확정"],
    }


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
    signal_score = abs(int(item.get("market_signal", {}).get("score", 0)))
    market_score = sum(1 for word in MARKET_TERMS if word.lower() in title.lower())
    priority = int(item.get("query_priority", 0))
    return (priority, market_score, signal_score, keyword_score, published)


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
    stances = Counter()
    tags = Counter()
    for article in articles:
        hits = score_article(article)
        signal = classify_article_signal(article)
        if hits:
            buckets.update(hits)
        stances.update([signal["stance"]])
        tags.update(signal["tags"])
        enriched.append({**article, "keyword_buckets": hits, "market_signal": signal})

    ranked = sorted(
        enriched,
        key=article_rank,
        reverse=True,
    )
    top_articles = ranked[:args.limit]
    dominant = buckets.most_common(3)
    dominant_stances = stances.most_common(3)
    dominant_tags = tags.most_common(5)

    if dominant:
        theme_text = ", ".join(f"{name}({count})" for name, count in dominant)
        stance_text = ", ".join(f"{name}({count})" for name, count in dominant_stances)
        interpretation = f"뉴스 키워드 기준으로는 {theme_text} 이슈가 상대적으로 많이 포착됩니다. 방향성은 {stance_text} 순입니다."
    else:
        interpretation = "시장 판단을 바꿀 만한 반복 키워드가 뚜렷하지 않아 신규 이슈는 공란에 가깝습니다."

    payload = {
        "analyzed_at": news.get("collected_at"),
        "provider": news.get("provider"),
        "recent_hours": args.recent_hours,
        "raw_article_count": len(raw_articles),
        "recent_article_count": len(articles),
        "dominant_buckets": [{"name": name, "count": count} for name, count in dominant],
        "dominant_stances": [{"name": name, "count": count} for name, count in dominant_stances],
        "dominant_signal_tags": [{"name": name, "count": count} for name, count in dominant_tags],
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
