import argparse
import json
from pathlib import Path


def fmt_number(value):
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


def fmt_pct(value):
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def direction_word(value):
    if value is None:
        return "확인 불가"
    if value > 0:
        return "상승"
    if value < 0:
        return "하락"
    return "보합"


def quote_metric(quote):
    return {
        "label": quote["label"],
        "value": fmt_number(quote["close"]),
        "note": f"시가 대비 {fmt_pct(quote.get('open_change_pct'))} · {quote.get('date')} {quote.get('time')}",
        "direction": quote.get("direction", "flat"),
    }


def quote_line(quote, pct_key="open_change_pct"):
    return f"{quote.get('label')} {fmt_number(quote.get('close'))}, 시가 대비 {fmt_pct(quote.get(pct_key))}"


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def parse_number(value):
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def metric_by_label(metrics):
    return {metric.get("label"): metric for metric in metrics if metric.get("label")}


def compare_metric_line(label, previous_metric, current_metric):
    previous_value = parse_number((previous_metric or {}).get("value"))
    current_value = parse_number((current_metric or {}).get("value"))
    if previous_value is None or current_value is None:
        return f"{label}: 비교 가능한 수치가 부족합니다."
    diff = current_value - previous_value
    diff_pct = (diff / previous_value * 100) if previous_value else 0
    sign = "+" if diff > 0 else ""
    previous_note = (previous_metric or {}).get("note", "")
    current_note = (current_metric or {}).get("note", "")
    return (
        f"{label}: 06시 {previous_value:,.2f}에서 현재 {current_value:,.2f}로 "
        f"{sign}{diff:,.2f}({sign}{diff_pct:.2f}%) 변화했습니다. "
        f"06시 근거: {previous_note} / 현재 근거: {current_note}"
    )


def judge_forecast_card(card, previous_metrics, current_metrics):
    title = card.get("title", "06시 예측")
    signal = card.get("signal", "")
    evidence = card.get("evidence", "")
    watch = card.get("watch", "")
    label_map = {
        "미국": ["S&P 500", "NASDAQ 100", "Dow Jones"],
        "국내": ["KOSPI", "KOSDAQ", "USD/KRW"],
        "리스크": ["Gold Futures", "USD/KRW"],
    }
    labels = []
    for key, values in label_map.items():
        if key in title or key in signal or key in watch:
            labels.extend(values)
    if not labels:
        labels = ["S&P 500", "NASDAQ 100", "Dow Jones", "Gold Futures", "USD/KRW"]
    lines = []
    movement_scores = []
    for label in dict.fromkeys(labels):
        prev_metric = previous_metrics.get(label)
        current_metric = current_metrics.get(label)
        if prev_metric and current_metric:
            lines.append(compare_metric_line(label, prev_metric, current_metric))
            prev_value = parse_number(prev_metric.get("value"))
            current_value = parse_number(current_metric.get("value"))
            if prev_value is not None and current_value is not None:
                movement_scores.append(abs((current_value - prev_value) / prev_value) if prev_value else 0)
    if not lines:
        verdict = "검증 보류"
        review = "06시 예측과 현재 데이터 사이에 직접 비교할 수 있는 지표가 부족합니다."
    else:
        max_move = max(movement_scores) if movement_scores else 0
        if max_move >= 0.01:
            verdict = "판단 수정 필요"
            review = "06시 예측 이후 핵심 지표 변화가 커졌습니다. 기존 방향을 그대로 유지하기보다 현재 수치 기준으로 강도와 리스크를 다시 잡아야 합니다."
        elif max_move >= 0.003:
            verdict = "부분 조정"
            review = "06시 방향성은 유지할 수 있지만, 일부 지표가 움직였기 때문에 업종별 강도와 환율·금 변수를 함께 재확인해야 합니다."
        else:
            verdict = "대체로 유지"
            review = "06시 예측 이후 핵심 수치 변화가 제한적입니다. 기존 판단을 유지하되 신규 뉴스가 있는지만 추가 확인하면 됩니다."
    return {
        "claim": f"{title}: {signal} / 06시 근거: {evidence}",
        "evidence": " ".join(lines) if lines else "비교 지표 없음",
        "verdict": verdict,
        "review": review,
    }


def build_history_comparison(payload, slot, history_dir):
    if slot == "0600":
        return {
            "status": "06시 기준 저장",
            "analysis": "오전 6시 자료는 오늘의 기준 예측으로 저장됩니다. 7시 이후 실행부터 이 예측과 실제 수치 변화를 비교합니다.",
            "changed_points": [
                "06시 예측 카드와 핵심 시장 지표를 히스토리에 저장",
                "07시 실행 시 미국장·국내장·금·환율 지표 변화폭을 자동 비교",
                "16시 실행 시 장중 흐름까지 반영해 예측 유지/수정 여부를 재판정",
            ],
            "review_items": [],
        }

    previous = read_json(Path(history_dir) / "latest" / "0600_summary.json", {})
    previous_summary = previous.get("summary", {}) if previous else {}
    if not previous_summary:
        return {
            "status": "비교 기준 없음",
            "analysis": "저장된 06시 예측 자료가 없어 이번 실행에서는 예측 검증을 보류합니다. 다음 06시 실행 이후부터 자동 비교가 가능합니다.",
            "changed_points": ["public/history/latest/0600_summary.json 파일이 아직 없습니다."],
            "review_items": [],
        }

    previous_metrics = metric_by_label(previous_summary.get("market_metrics", []))
    current_metrics = metric_by_label(payload.get("summary", {}).get("metrics", []))
    tracked_labels = ["S&P 500", "NASDAQ 100", "Dow Jones", "Gold Futures", "USD/KRW", "KOSPI", "KOSDAQ"]
    changed_points = [
        compare_metric_line(label, previous_metrics.get(label), current_metrics.get(label))
        for label in tracked_labels
        if previous_metrics.get(label) or current_metrics.get(label)
    ]
    review_items = [
        judge_forecast_card(card, previous_metrics, current_metrics)
        for card in previous_summary.get("forecast_cards", [])
    ]
    if not review_items:
        review_items = [{
            "claim": "06시 예측 카드",
            "evidence": "저장된 예측 카드가 없습니다.",
            "verdict": "검증 보류",
            "review": "핵심 지표 비교는 가능하지만 예측 문장 단위의 검증은 다음 06시 저장 이후 가능합니다.",
        }]

    verdict_counts = {}
    for item in review_items:
        verdict_counts[item["verdict"]] = verdict_counts.get(item["verdict"], 0) + 1
    verdict_text = ", ".join(f"{name} {count}건" for name, count in verdict_counts.items())
    return {
        "status": "예측 검증 완료",
        "analysis": (
            f"저장된 06시 예측({previous.get('saved_at', '시간 미상')})과 현재 {slot} 실행 데이터를 비교했습니다. "
            f"검증 결과는 {verdict_text or '검증 항목 없음'}입니다. 수치 변화가 큰 항목은 기존 방향성보다 현재 지표를 우선해 해석합니다."
        ),
        "changed_points": changed_points or ["비교 가능한 핵심 지표 변화가 없습니다."],
        "review_items": review_items,
    }


def market_charts():
    return [
        {
            "title": "KOSPI 일중 차트",
            "caption": "네이버 금융 공개 차트 이미지",
            "image_url": "https://ssl.pstatic.net/imgfinance/chart/sise/siseMainKOSPI.png",
            "source_url": "https://finance.naver.com/sise/sise_index.naver?code=KOSPI",
        },
        {
            "title": "KOSDAQ 일중 차트",
            "caption": "네이버 금융 공개 차트 이미지",
            "image_url": "https://ssl.pstatic.net/imgfinance/chart/sise/siseMainKOSDAQ.png",
            "source_url": "https://finance.naver.com/sise/sise_index.naver?code=KOSDAQ",
        },
    ]


def strongest_weakest(quotes, pct_key):
    valid = [item for item in quotes if item.get(pct_key) is not None]
    if not valid:
        return None, None
    ranked = sorted(valid, key=lambda item: item[pct_key], reverse=True)
    return ranked[0], ranked[-1]


def format_signal_item(item, pct_key):
    if not item:
        return "N/A"
    return f"{item.get('label')} {fmt_pct(item.get(pct_key))}"


def build_forecast_cards(us_quotes, kr_indexes, gold, usdkrw, news_analysis):
    cards = []
    us_best, us_worst = strongest_weakest(us_quotes, "open_change_pct")
    if us_quotes:
        us_up = len([quote for quote in us_quotes if (quote.get("open_change_pct") or 0) > 0])
        us_down = len([quote for quote in us_quotes if (quote.get("open_change_pct") or 0) < 0])
        if us_up and us_down:
            signal = "미국장 혼조"
            implication = "지수 전체 방향보다 어떤 지수가 버티는지 확인해야 합니다. NASDAQ이 상대적으로 강하면 성장주, Dow가 약하면 경기민감주 부담으로 나눠 봅니다."
        elif us_up:
            signal = "미국장 상승 우위"
            implication = "미국장 자체는 위험선호 쪽입니다. 국내장에서는 반도체/성장주가 이를 받아내는지 확인합니다."
        else:
            signal = "미국장 하락 우위"
            implication = "국내장 초반에는 방어적 해석이 우선입니다. 환율과 외국인 수급을 같이 봐야 합니다."
        cards.append({
            "title": "1. 미국장이 남긴 신호",
            "signal": signal,
            "evidence": f"가장 강한 지수: {format_signal_item(us_best, 'open_change_pct')} / 가장 약한 지수: {format_signal_item(us_worst, 'open_change_pct')}",
            "implication": implication,
            "watch": "KOSPI 대형주, 반도체, 외국인 순매수",
        })

    if kr_indexes or usdkrw:
        kr_best, kr_worst = strongest_weakest(kr_indexes, "change_pct")
        kr_weak = len([index for index in kr_indexes if (index.get("change_pct") or 0) < 0])
        usdkrw_text = quote_line(usdkrw) if usdkrw else "환율 N/A"
        signal = "국내장 약세 확인" if kr_weak else "국내장 방어 확인"
        implication = "환율과 지수가 같은 방향으로 불안하면 위험회피가 강합니다. 지수만 약하면 국내 수급/업종 이슈를 별도로 확인해야 합니다."
        cards.append({
            "title": "2. 국내장이 확인해야 할 것",
            "signal": signal,
            "evidence": f"가장 강한 국내 지수: {format_signal_item(kr_best, 'change_pct')} / 가장 약한 국내 지수: {format_signal_item(kr_worst, 'change_pct')} / {usdkrw_text}",
            "implication": implication,
            "watch": "외국인 수급, 원/달러, KOSPI·KOSDAQ 동반성",
        })

    if gold or news_analysis:
        news_count = (news_analysis or {}).get("recent_article_count", 0)
        gold_text = quote_line(gold) if gold else "금 N/A"
        signal = "헤지 수요 점검" if gold and (gold.get("open_change_pct") or 0) > 0 else "헤지 수요 약화 또는 중립"
        cards.append({
            "title": "3. 리스크 변수",
            "signal": signal,
            "evidence": f"{gold_text} / 최근 뉴스 필터 통과 {news_count}건",
            "implication": "금, 환율, 뉴스가 같은 방향으로 움직일 때만 강한 위험회피 신호로 봅니다. 하나만 움직이면 보조 신호로 취급합니다.",
            "watch": "금, 원/달러, 유가·금리 뉴스",
        })
    return cards


def market_summary_from_quotes(us_quotes):
    if not us_quotes:
        return "미국장 데이터가 수집되지 않았습니다."
    parts = []
    for quote in us_quotes:
        pct = quote.get("open_change_pct")
        parts.append(f"{quote.get('label')}은 {fmt_number(quote.get('close'))}로 시가 대비 {fmt_pct(pct)}입니다")
    positives = [quote for quote in us_quotes if (quote.get("open_change_pct") or 0) > 0]
    negatives = [quote for quote in us_quotes if (quote.get("open_change_pct") or 0) < 0]
    if positives and negatives:
        tail = "지수별 방향이 엇갈려 미국장은 혼조로 요약됩니다."
    elif positives:
        tail = "세 지수가 모두 시가 대비 상승해 미국장은 상승 우위로 요약됩니다."
    elif negatives:
        tail = "세 지수가 모두 시가 대비 하락해 미국장은 하락 우위로 요약됩니다."
    else:
        tail = "세 지수 모두 큰 방향성이 뚜렷하지 않습니다."
    return " ".join(parts) + ". " + tail


def gold_summary_from_data(gold, usdkrw):
    if not gold:
        return "금 데이터가 수집되지 않았습니다."
    parts = [f"금 선물은 {fmt_number(gold.get('close'))}로 시가 대비 {fmt_pct(gold.get('open_change_pct'))}입니다"]
    if usdkrw:
        parts.append(f"원/달러 환율은 {fmt_number(usdkrw.get('close'))}로 시가 대비 {fmt_pct(usdkrw.get('open_change_pct'))}입니다")
    gold_pct = gold.get("open_change_pct")
    usdkrw_pct = (usdkrw or {}).get("open_change_pct")
    if gold_pct is not None and gold_pct < 0:
        tail = "현재 수치만 보면 금 가격은 상승 압력보다 약세 쪽으로 표시됩니다."
    elif gold_pct is not None and gold_pct > 0 and usdkrw_pct is not None:
        tail = "금과 환율을 함께 보며 안전자산 수요와 달러 흐름이 같은 방향인지 확인합니다."
    else:
        tail = "금 가격 방향을 먼저 확인하고 달러/금리 자료로 보완해야 합니다."
    return " ".join(parts) + ". " + tail


def kr_summary_from_data(indexes, usdkrw):
    if not indexes:
        return "국내장 데이터가 수집되지 않았습니다."
    parts = []
    for index in indexes:
        parts.append(f"{index.get('label')}는 {fmt_number(index.get('close'))}로 전일 대비 {fmt_pct(index.get('change_pct'))}입니다")
    if usdkrw:
        parts.append(f"원/달러 환율은 {fmt_number(usdkrw.get('close'))}로 시가 대비 {fmt_pct(usdkrw.get('open_change_pct'))}입니다")
    weak = [index for index in indexes if (index.get("change_pct") or 0) < 0]
    strong = [index for index in indexes if (index.get("change_pct") or 0) > 0]
    if weak and not strong:
        tail = "국내 지수는 하락 우위로 요약됩니다."
    elif strong and not weak:
        tail = "국내 지수는 상승 우위로 요약됩니다."
    else:
        tail = "국내 지수는 혼조로 요약됩니다."
    return " ".join(parts) + ". " + tail


def real_estate_summary_from_data(rone, molit_info):
    metrics = (rone or {}).get("metrics", [])
    if not metrics and not molit_info:
        return "부동산 공개자료가 수집되지 않았습니다."
    selected = []
    for metric in metrics[:6]:
        selected.append(f"{metric.get('period')} {metric.get('survey')}의 {metric.get('descriptor')}은 {metric.get('raw_value')}입니다")
    release = (molit_info or {}).get("real_trade", {}).get("latest_release", {})
    facts = release.get("facts", [])
    if release.get("title"):
        selected.append(f"실거래가 공개시스템 최신 보도자료는 {release.get('date')} 기준 '{release.get('title')}'입니다")
    if len(facts) > 1:
        selected.append(facts[1])
    if not selected:
        return "부동산 공개자료는 수집됐지만 요약 가능한 핵심 항목이 부족합니다."
    return " ".join(selected[:8])


def policy_summary_from_data(molit_info):
    policy_news = (molit_info or {}).get("molit", {}).get("policy_news", [])
    if not policy_news:
        return "국토교통부 정책뉴스 항목이 수집되지 않았습니다."
    lines = []
    for item in policy_news[:5]:
        lines.append(f"{item.get('date')} {item.get('category')} 항목으로 '{item.get('title')}'가 게시되어 있습니다")
    return " ".join(lines)


def fresh_news_summary_from_data(news_analysis):
    if not news_analysis:
        return "뉴스 분석 자료가 없습니다."
    count = news_analysis.get("recent_article_count", 0)
    if count == 0:
        return f"Google News RSS 원자료 {news_analysis.get('raw_article_count', 0)}건 중 최근 36시간 필터를 통과한 기사가 없어 신규 이슈는 공란으로 둡니다."
    dominant = ", ".join(f"{item['name']} {item['count']}건" for item in news_analysis.get("dominant_buckets", []))
    top = news_analysis.get("top_articles", [])
    top_line = ""
    if top:
        first = top[0]
        top_line = f" 대표 기사는 {first.get('published_at')}에 {first.get('publisher')}가 게시한 '{first.get('title')}'입니다."
    return f"Google News RSS 원자료 {news_analysis.get('raw_article_count', 0)}건 중 최근 36시간 필터를 통과한 기사는 {count}건입니다. 반복 키워드는 {dominant or '없음'}입니다.{top_line}"


def index_metric(index):
    value = index.get("close")
    change_pct = index.get("change_pct")
    if change_pct is None:
        change_note = "전일 대비 N/A"
    else:
        sign = "+" if change_pct > 0 else ""
        change_note = f"전일 대비 {sign}{change_pct:.2f}%"
    return {
        "label": index["label"],
        "value": fmt_number(value),
        "note": f"{change_note} · 공개 페이지",
        "direction": index.get("direction", "flat"),
    }


def rone_metric(metric):
    value = metric.get("raw_value")
    descriptor = metric.get("descriptor", "")
    suffix = "%" if "변동률" in descriptor or "지수" in descriptor else ""
    return {
        "label": metric.get("survey", ""),
        "value": f"{value}{suffix}",
        "note": f"{metric.get('period', '')} · {descriptor}",
        "direction": metric.get("direction", "flat"),
    }


def article_lines(news_analysis, limit=6):
    lines = []
    for article in news_analysis.get("top_articles", [])[:limit]:
        published = article.get("published_at") or "시간 미확인"
        publisher = article.get("publisher") or "출처 미확인"
        lines.append(f"{article.get('title', '')} · {publisher} · {published}")
    return lines


def policy_lines(molit_info, limit=8):
    items = []
    for item in molit_info.get("molit", {}).get("policy_news", [])[:limit]:
        items.append(f"{item.get('date')} · {item.get('category')} · {item.get('title')}")
    return items


def real_trade_lines(molit_info, limit=8):
    release = molit_info.get("real_trade", {}).get("latest_release", {})
    lines = []
    if release.get("title"):
        lines.append(f"{release.get('date')} · {release.get('title')}")
    lines.extend(release.get("facts", [])[:limit])
    return lines


def build_us_review(us_quotes):
    if not us_quotes:
        return []
    ups = [quote for quote in us_quotes if quote.get("open_change_pct", 0) > 0]
    downs = [quote for quote in us_quotes if quote.get("open_change_pct", 0) < 0]
    evidence = " / ".join(quote_line(quote) for quote in us_quotes)
    if ups and downs:
        verdict = "부분 일치"
        review = "나스닥/S&P와 다우의 방향이 갈려 단일한 위험선호로 보기 어렵습니다. 성장주 쪽은 상대적으로 버티지만 경기민감 대형주는 약한 혼조 장세로 해석하는 편이 더 정확합니다."
    elif ups:
        verdict = "대체로 일치"
        review = "주요 지수가 모두 시가 대비 상승해 위험선호가 우세하다는 설명과 잘 맞습니다."
    else:
        verdict = "주의 필요"
        review = "주요 지수가 모두 약해 성장주 완충 기대보다 위험회피 설명을 우선해야 합니다."
    return [{
        "claim": "미국장 흐름은 국내장 초반 방향을 정하는 1차 변수이며, 성장주가 견조하면 국내 대형 성장주에 완충 요인이 됩니다.",
        "evidence": evidence,
        "verdict": verdict,
        "review": review,
    }]


def us_detail_items(us_quotes, gold, usdkrw):
    if not us_quotes:
        return []
    best, worst = strongest_weakest(us_quotes, "open_change_pct")
    items = [
        f"지수 강도: {format_signal_item(best, 'open_change_pct')}가 가장 강하고, {format_signal_item(worst, 'open_change_pct')}가 가장 약합니다.",
        "해석 순서: 세 지수가 같은 방향이면 시장 전체 심리, 엇갈리면 성장주와 경기민감주의 차이를 먼저 봅니다.",
    ]
    if gold:
        items.append(f"금 동조 확인: {quote_line(gold)}")
    if usdkrw:
        items.append(f"달러/원화 확인: {quote_line(usdkrw)}")
    items.append("한국장 연결: NASDAQ 강세는 성장주/반도체에 우호적일 수 있고, Dow 약세는 경기민감 업종 부담으로 볼 수 있습니다.")
    return items


def build_gold_review(gold, usdkrw):
    if not gold:
        return []
    evidence_parts = [quote_line(gold)]
    if usdkrw:
        evidence_parts.append(quote_line(usdkrw))
    gold_pct = gold.get("open_change_pct")
    usdkrw_pct = (usdkrw or {}).get("open_change_pct")
    if gold_pct and gold_pct > 0 and usdkrw_pct is not None and usdkrw_pct <= 0:
        verdict = "보강 필요"
        review = "금은 상승했지만 원/달러가 약하지 않아 단순 달러강세형 위험회피로 보기는 어렵습니다. 금리, 유가, 지정학 뉴스와 함께 추가 확인해야 합니다."
    elif gold_pct and gold_pct > 0:
        verdict = "대체로 일치"
        review = "금이 상승해 안전자산 또는 인플레이션 헤지 수요가 붙었다는 설명과 방향은 맞습니다."
    else:
        verdict = "주의 필요"
        review = "금이 약하면 위험회피 설명은 약해지고, 주식/달러/금리 쪽 설명을 우선해야 합니다."
    return [{
        "claim": "금 가격은 달러, 금리, 위험회피 심리의 교차점이며 상승 시 시장 불안 또는 헤지 수요를 시사할 수 있습니다.",
        "evidence": " / ".join(evidence_parts),
        "verdict": verdict,
        "review": review,
    }]


def build_kr_review(indexes, usdkrw):
    if not indexes:
        return []
    evidence_parts = []
    for index in indexes:
        evidence_parts.append(f"{index.get('label')} {fmt_number(index.get('close'))}, 전일 대비 {fmt_pct(index.get('change_pct'))}")
    if usdkrw:
        evidence_parts.append(quote_line(usdkrw))
    weak_indexes = [index for index in indexes if (index.get("change_pct") or 0) < 0]
    if weak_indexes and usdkrw and (usdkrw.get("open_change_pct") or 0) <= 0:
        verdict = "부분 일치"
        review = "환율은 안정적인 편이지만 국내 지수는 약합니다. 따라서 환율보다 국내 수급, 업종별 매도, 전일 미국장 혼조를 함께 봐야 합니다."
    elif weak_indexes:
        verdict = "주의 필요"
        review = "국내 지수가 하락해 장 초반 민감도는 방어보다 위험회피 쪽으로 읽어야 합니다."
    else:
        verdict = "대체로 일치"
        review = "국내 지수가 상승 또는 보합권이면 환율 안정과 미국 성장주 흐름이 완충 요인이라는 설명이 비교적 잘 맞습니다."
    return [{
        "claim": "국내장은 원/달러 환율 안정 여부와 외국인 수급 확인이 우선이며, KOSPI/KOSDAQ 방향을 함께 봐야 합니다.",
        "evidence": " / ".join(evidence_parts),
        "verdict": verdict,
        "review": review,
    }]


def build_real_estate_review(rone, molit_info):
    items = []
    metrics = (rone or {}).get("metrics", [])
    metric_map = {metric.get("descriptor", ""): metric for metric in metrics}
    apartment_sale = next((metric for metric in metrics if metric.get("survey") == "전국주택가격동향조사" and "매매가격" in metric.get("descriptor", "")), None)
    actual_sale = next((metric for metric in metrics if metric.get("survey") == "공동주택실거래가격지수"), None)
    jeonse = next((metric for metric in metrics if "전세가격" in metric.get("descriptor", "")), None)
    officetel = next((metric for metric in metrics if metric.get("survey") == "오피스텔가격동향조사"), None)
    release = (molit_info or {}).get("real_trade", {}).get("latest_release", {})
    facts = release.get("facts", [])
    evidence = []
    for metric in [apartment_sale, actual_sale, jeonse, officetel]:
        if metric:
            evidence.append(f"{metric.get('period')} {metric.get('survey')} {metric.get('descriptor')} {metric.get('raw_value')}")
    if facts:
        evidence.append(facts[1] if len(facts) > 1 else facts[0])
    if evidence:
        items.append({
            "claim": "주택 가격지표는 플러스권이지만, 부동산 전체를 강한 회복으로 단정하기보다 유형별 차이를 봐야 합니다.",
            "evidence": " / ".join(evidence),
            "verdict": "대체로 일치",
            "review": "아파트 매매와 실거래 지수는 상승권이고 전세도 플러스지만, 오피스텔 또는 상업용 지표는 약한 항목이 있어 회복 강도는 균일하지 않습니다. 미분양 감소와 준공 후 미분양 증가는 동시에 확인해야 합니다.",
        })
    return items


def build_policy_review(molit_info):
    policy_news = (molit_info or {}).get("molit", {}).get("policy_news", [])
    if not policy_news:
        return []
    housing_items = [item for item in policy_news if "주택" in item.get("category", "") or "주택" in item.get("title", "") or "공시가격" in item.get("title", "")]
    evidence = " / ".join(f"{item.get('date')} {item.get('category')} {item.get('title')}" for item in policy_news[:4])
    if housing_items:
        verdict = "일치"
        review = "정책뉴스에서 주택통계, 공시가격, 지가 관련 항목이 확인되어 부동산 섹션과 직접 연결할 근거가 있습니다."
    else:
        verdict = "보강 필요"
        review = "정책뉴스가 교통/모빌리티 중심이면 부동산 정책 영향은 보조적으로만 다루는 편이 맞습니다."
    return [{
        "claim": "정책 흐름은 주택공급, 공시가격, 지가, 주거지원 항목이 있을 때 부동산 시장 해석에 직접 연결됩니다.",
        "evidence": evidence,
        "verdict": verdict,
        "review": review,
    }]


def build_fresh_news_review(news_analysis):
    if not news_analysis:
        return []
    count = news_analysis.get("recent_article_count", 0)
    dominant = ", ".join(f"{item['name']} {item['count']}건" for item in news_analysis.get("dominant_buckets", []))
    top = news_analysis.get("top_articles", [])
    evidence = dominant or "최근 36시간 필터 기준 반복 키워드 없음"
    if top:
        evidence += " / 대표 기사: " + top[0].get("title", "")
    return [{
        "claim": "당일 신규 정보는 최근 36시간 안에 들어온 기사만 시장 판단 재료로 사용합니다.",
        "evidence": f"원자료 {news_analysis.get('raw_article_count', 0)}건 중 최근 필터 통과 {count}건. {evidence}",
        "verdict": "검토 완료" if count else "공란 유지",
        "review": "오래된 관련 기사는 제외하고 최근 기사만 남겼습니다. 통과 건수가 적으면 시장 판단을 과하게 바꾸지 않는 것이 맞습니다.",
    }]


def page_lines(page_probe):
    lines = []
    for page in page_probe.get("pages", []):
        status = "접근 가능" if page.get("status") == "reachable" else "점검 필요"
        title = page.get("title") or page.get("label")
        lines.append(f"{page.get('label')} · {status} · {title}")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--news-analysis")
    parser.add_argument("--kr-market")
    parser.add_argument("--page-probe")
    parser.add_argument("--rone")
    parser.add_argument("--molit-info")
    parser.add_argument("--slot", default="0600", choices=("0600", "0700", "1600"))
    parser.add_argument("--history-dir", default="public/history")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.base).read_text(encoding="utf-8"))
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    news_analysis = None
    if args.news_analysis:
        news_analysis = json.loads(Path(args.news_analysis).read_text(encoding="utf-8"))
    kr_market = None
    if args.kr_market:
        kr_market = json.loads(Path(args.kr_market).read_text(encoding="utf-8"))
    page_probe = None
    if args.page_probe:
        page_probe = json.loads(Path(args.page_probe).read_text(encoding="utf-8"))
    rone = None
    if args.rone:
        rone = json.loads(Path(args.rone).read_text(encoding="utf-8"))
    molit_info = None
    if args.molit_info:
        molit_info = json.loads(Path(args.molit_info).read_text(encoding="utf-8"))
    quotes = {quote["id"]: quote for quote in snapshot["quotes"]}

    payload["generated_at"] = snapshot["collected_at"]
    payload["summary"]["headline"] = "실제 시장 스냅샷과 뉴스 흐름을 반영한 1차 데이터 분석 리포트입니다."
    payload["summary"]["stance"] = "데이터 반영"
    payload["summary"]["metrics"] = [quote_metric(q) for q in snapshot["quotes"]]
    payload["summary"]["charts"] = market_charts()
    payload["summary"]["source_urls"] = sorted({q["source_url"] for q in snapshot["quotes"]})
    if news_analysis:
        payload["summary"]["source_urls"] = sorted(set(payload["summary"]["source_urls"]) | set(news_analysis.get("source_urls", [])))
    if kr_market:
        payload["summary"]["source_urls"] = sorted(set(payload["summary"]["source_urls"]) | {row["source_url"] for row in kr_market.get("indexes", [])})
    if rone:
        payload["summary"]["source_urls"] = sorted(set(payload["summary"]["source_urls"]) | {rone["source_url"]})
    if molit_info:
        payload["summary"]["source_urls"] = sorted(set(payload["summary"]["source_urls"]) | {
            molit_info["molit"]["source_url"],
            molit_info["real_trade"]["source_url"],
        })

    us_quotes = [quotes[key] for key in ("spx", "nasdaq", "dow") if key in quotes]
    gold = quotes.get("gold")
    usdkrw = quotes.get("usdkrw")

    kr_indexes = (kr_market or {}).get("indexes", [])
    payload["forecast_0600"]["prediction"] = " ".join([
        market_summary_from_quotes(us_quotes),
        kr_summary_from_data(kr_indexes, usdkrw),
        gold_summary_from_data(gold, usdkrw),
    ])
    payload["forecast_0600"]["insight_cards"] = build_forecast_cards(us_quotes, kr_indexes, gold, usdkrw, news_analysis)
    payload["forecast_0600"]["source_urls"] = payload["summary"]["source_urls"]

    history_comparison = build_history_comparison(payload, args.slot, args.history_dir)
    payload["comparison_0700"]["status"] = history_comparison["status"]
    payload["comparison_0700"]["analysis"] = history_comparison["analysis"]
    payload["comparison_0700"]["changed_points"] = history_comparison["changed_points"]
    payload["comparison_0700"]["review_items"] = history_comparison["review_items"]
    payload["comparison_0700"]["source_urls"] = payload["summary"]["source_urls"]

    for section in payload["sections"]:
        if section["id"] == "fresh_news" and news_analysis:
            top_articles = news_analysis.get("top_articles", [])
            section["status"] = "뉴스 RSS 반영" if top_articles else "공란"
            section["body"] = fresh_news_summary_from_data(news_analysis)
            section["items"] = article_lines(news_analysis)
            section["review_items"] = build_fresh_news_review(news_analysis)
            section["source_urls"] = news_analysis.get("source_urls", [])
        if section["id"] == "us_market":
            section["status"] = "실제 데이터 반영"
            section["body"] = market_summary_from_quotes(us_quotes)
            section["metrics"] = [quote_metric(q) for q in us_quotes]
            section["items"] = us_detail_items(us_quotes, gold, usdkrw)
            section["review_items"] = build_us_review(us_quotes)
            section["source_urls"] = [q["source_url"] for q in us_quotes]
        elif section["id"] == "gold" and gold:
            section["status"] = "실제 데이터 반영"
            section["body"] = gold_summary_from_data(gold, usdkrw)
            section["metrics"] = [quote_metric(gold)]
            section["review_items"] = build_gold_review(gold, usdkrw)
            section["source_urls"] = [gold["source_url"]]
        elif section["id"] == "kr_market":
            if kr_market:
                section["status"] = "공개 페이지 반영"
                section["body"] = kr_summary_from_data(kr_market.get("indexes", []), usdkrw)
                section["metrics"] = [index_metric(row) for row in kr_market.get("indexes", [])]
                if usdkrw:
                    section["metrics"].append(quote_metric(usdkrw))
                section["review_items"] = build_kr_review(kr_market.get("indexes", []), usdkrw)
                section["source_urls"] = [row["source_url"] for row in kr_market.get("indexes", [])]
                if usdkrw:
                    section["source_urls"].append(usdkrw["source_url"])
            else:
                section["status"] = "공개 페이지 연결 대기"
                section["body"] = "국내장 지수와 수급은 네이버 금융/KRX 공개 페이지를 브라우저 자동화로 읽는 방식으로 처리합니다."
                section["metrics"] = [quote_metric(usdkrw)] if usdkrw else []
                section["source_urls"] = [usdkrw["source_url"]] if usdkrw else []
        elif section["id"] == "real_estate":
            if rone or molit_info:
                section["status"] = "실제 공개자료 반영"
                section["body"] = real_estate_summary_from_data(rone, molit_info)
                section["metrics"] = [rone_metric(metric) for metric in (rone or {}).get("metrics", [])[:6]]
                section["items"] = real_trade_lines(molit_info or {})
                section["review_items"] = build_real_estate_review(rone, molit_info)
                section["source_urls"] = []
                if rone:
                    section["source_urls"].append(rone["source_url"])
                if molit_info:
                    section["source_urls"].append(molit_info["real_trade"]["source_url"])
            elif page_probe:
                section["status"] = "브라우저 접근 점검"
                section["body"] = "부동산은 API 없이 국토교통부 실거래가 공개시스템과 한국부동산원 R-ONE 공개 페이지를 브라우저 자동화로 조회하는 구조입니다. 현재 단계에서는 접근 가능 여부와 출처 URL을 리포트에 반영합니다."
                real_pages = [page for page in page_probe.get("pages", []) if page.get("id") in ("molit_real_trade", "reb_rone")]
                section["items"] = page_lines({"pages": real_pages})
                section["source_urls"] = [page["url"] for page in real_pages]
        elif section["id"] == "policy":
            if molit_info:
                section["status"] = "실제 공개자료 반영"
                section["body"] = policy_summary_from_data(molit_info)
                section["items"] = policy_lines(molit_info)
                section["review_items"] = build_policy_review(molit_info)
                section["source_urls"] = [molit_info["molit"]["source_url"]]
            elif page_probe:
                section["status"] = "브라우저 접근 점검"
                section["body"] = "정책은 정부/국토교통부 공개 페이지를 브라우저 자동화로 방문해 보도자료와 정책자료를 확인하는 방식으로 설계했습니다. 페이지 문구는 분석 근거로만 쓰고, 지시문처럼 보이는 웹 내용은 실행하지 않습니다."
                policy_pages = [page for page in page_probe.get("pages", []) if page.get("id") in ("molit_policy", "krx", "naver_finance")]
                section["items"] = page_lines({"pages": policy_pages})
                section["source_urls"] = [page["url"] for page in policy_pages]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
