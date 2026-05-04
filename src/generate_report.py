import argparse
import html
import json
from pathlib import Path


def esc(value):
    return html.escape(str(value), quote=True)


def render_source_urls(urls):
    if not urls:
        return '<p class="empty">출처 URL: 공란</p>'
    links = []
    for url in urls:
        safe_url = esc(url)
        links.append(f'<li><a href="{safe_url}" target="_blank" rel="noreferrer">{safe_url}</a></li>')
    return (
        f'<details class="source-details">'
        f'<summary>출처 보기 <span>{len(urls)}</span></summary>'
        f'<div class="source-scroll"><ul class="sources">'
        + ''.join(links)
        + '</ul></div></details>'
    )


def render_list(items):
    if not items:
        return '<p class="empty">공란</p>'
    return '<ul>' + ''.join(f'<li>{esc(item)}</li>' for item in items) + '</ul>'


def render_items(items):
    if not items:
        return ""
    rows = []
    for item in items:
        rows.append(f'<li class="news-item">{esc(item)}</li>')
    return '<h3>주요 항목</h3><ul class="news-list">' + ''.join(rows) + '</ul>'


def render_metrics(metrics):
    if not metrics:
        return ""
    cards = []
    for metric in metrics:
        direction = metric.get("direction", "flat")
        cards.append(f"""
        <article class="metric metric-{esc(direction)}">
          <div class="metric-label">{esc(metric.get("label", ""))}</div>
          <div class="metric-value">{esc(metric.get("value", ""))}</div>
          <div class="metric-note">{esc(metric.get("note", ""))}</div>
        </article>
        """)
    return '<section class="metrics">' + ''.join(cards) + '</section>'


def render_charts(charts):
    if not charts:
        return ""
    cards = []
    for chart in charts:
        image_url = esc(chart.get("image_url", ""))
        source_url = esc(chart.get("source_url", ""))
        cards.append(f"""
        <article class="chart-card">
          <div class="chart-head">
            <strong>{esc(chart.get("title", ""))}</strong>
            <a href="{source_url}" target="_blank" rel="noreferrer">원본</a>
          </div>
          <img src="{image_url}" alt="{esc(chart.get("title", ""))}">
          <p>{esc(chart.get("caption", ""))}</p>
        </article>
        """)
    return '<section class="chart-board">' + ''.join(cards) + '</section>'


def render_insight_cards(cards):
    if not cards:
        return ""
    rows = []
    for card in cards:
        rows.append(f"""
        <article class="insight-card">
          <div class="insight-title">{esc(card.get("title", ""))}</div>
          <div class="insight-signal">{esc(card.get("signal", ""))}</div>
          <dl>
            <dt>근거</dt><dd>{esc(card.get("evidence", ""))}</dd>
            <dt>시사점</dt><dd>{esc(card.get("implication", ""))}</dd>
            <dt>확인할 것</dt><dd>{esc(card.get("watch", ""))}</dd>
          </dl>
        </article>
        """)
    return '<section class="insight-grid">' + ''.join(rows) + '</section>'


def render_review_items(items):
    if not items:
        return ""
    rows = []
    for item in items:
        rows.append(f"""
        <article class="review-card">
          <div class="review-verdict">{esc(item.get("verdict", ""))}</div>
          <div class="review-row"><strong>설명</strong><p>{esc(item.get("claim", ""))}</p></div>
          <div class="review-row"><strong>실제 근거</strong><p>{esc(item.get("evidence", ""))}</p></div>
          <div class="review-row"><strong>검토</strong><p>{esc(item.get("review", ""))}</p></div>
        </article>
        """)
    return '<h3>설명-근거 검토</h3><section class="review-grid">' + ''.join(rows) + '</section>'


def render_news_market_check(check):
    if not check:
        return ""
    rows = []
    for item in check.get("items", []):
        rows.append(f"""
        <article class="cross-card">
          <div class="cross-top">
            <strong>{esc(item.get("theme", ""))}</strong>
            <span>{esc(item.get("verdict", ""))}</span>
          </div>
          <dl>
            <dt>뉴스 신호</dt><dd>{esc(item.get("news_signal", ""))}</dd>
            <dt>시장 신호</dt><dd>{esc(item.get("market_signal", ""))}</dd>
            <dt>판단</dt><dd>{esc(item.get("analysis", ""))}</dd>
          </dl>
        </article>
        """)
    return f"""
    <section class="panel cross-check">
      <div class="section-head">
        <h2>뉴스-시장 교차검증</h2>
        <span class="badge">{esc(check.get("status", ""))}</span>
      </div>
      <p>{esc(check.get("headline", ""))}</p>
      <section class="cross-grid">{''.join(rows)}</section>
      <h3>출처 URL</h3>
      {render_source_urls(check.get("source_urls", []))}
    </section>
    """


def render_key_takeaways(items):
    if not items:
        return ""
    rows = []
    for item in items[:3]:
        rows.append(f"""
        <article class="takeaway-card">
          <strong>{esc(item.get("label", ""))}</strong>
          <p>{esc(item.get("text", ""))}</p>
          <span>{esc(item.get("basis", ""))}</span>
        </article>
        """)
    return '<section class="takeaways" aria-label="오늘의 핵심 결론">' + ''.join(rows) + '</section>'


def render_section(section):
    status = esc(section.get("status", ""))
    return f"""
    <section class="panel">
      <div class="section-head">
        <h2>{esc(section.get("title", ""))}</h2>
        <span class="badge">{status}</span>
      </div>
      <p>{esc(section.get("body", ""))}</p>
      {render_metrics(section.get("metrics", []))}
      {render_items(section.get("items", []))}
      {render_review_items(section.get("review_items", []))}
      <h3>출처 URL</h3>
      {render_source_urls(section.get("source_urls", []))}
    </section>
    """


def render_report(payload):
    forecast = payload["forecast_0600"]
    comparison = payload["comparison_0700"]
    sections = "\n".join(render_section(section) for section in payload.get("sections", []))
    news_market_check = render_news_market_check(payload.get("news_market_check"))
    key_takeaways = render_key_takeaways(payload.get("key_takeaways", []))

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(payload.get("title", "경제 데일리 브리핑"))}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7f8;
      --ink: #172026;
      --muted: #66727c;
      --line: #dfe5e8;
      --panel: #ffffff;
      --accent: #0f6f73;
      --accent-soft: #e7f3f2;
      --warn: #9b5b00;
      --down: #1e63a3;
      --up: #b33d32;
      --gold: #a36f00;
      --shadow: 0 12px 30px rgba(23, 32, 38, 0.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, "Malgun Gothic", sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.62;
    }}
    header {{
      background:
        linear-gradient(135deg, rgba(15, 111, 115, 0.14), rgba(163, 111, 0, 0.07)),
        #ffffff;
      border-bottom: 1px solid var(--line);
    }}
    .wrap {{
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .hero {{
      padding: 34px 0 28px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .meta, .empty {{
      color: var(--muted);
      font-size: 14px;
    }}
    main {{
      padding: 22px 0 40px;
    }}
    .topbar {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 18px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      padding: 4px 10px;
      border: 1px solid rgba(15, 111, 115, 0.22);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.62);
      color: #164c50;
      font-size: 13px;
      text-decoration: none;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 16px;
      box-shadow: var(--shadow);
    }}
    .lead {{
      border-left: 4px solid var(--accent);
      display: grid;
      gap: 6px;
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 12px 14px;
      box-shadow: 0 8px 20px rgba(23, 32, 38, 0.07);
    }}
    .lead h2 {{
      font-size: 13px;
      line-height: 1.35;
      font-weight: 600;
      color: var(--muted);
    }}
    .lead h3 {{
      margin: 6px 0 4px;
      font-size: 12px;
    }}
    .lead .badge {{
      min-height: 22px;
      padding: 2px 8px;
      font-size: 11px;
    }}
    .lead .metrics {{
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 6px;
      margin-top: 4px;
    }}
    .lead .metric {{
      min-height: 58px;
      padding: 7px 8px;
    }}
    .lead .metric-label {{
      font-size: 10px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .lead .metric-value {{
      margin-top: 2px;
      font-size: 15px;
    }}
    .lead .metric-note {{
      margin-top: 2px;
      font-size: 10px;
      line-height: 1.25;
      display: -webkit-box;
      -webkit-line-clamp: 1;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .takeaways {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .takeaway-card {{
      min-height: 148px;
      border: 1px solid #d7e2e1;
      border-radius: 8px;
      background: #fbfdfd;
      padding: 14px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .takeaway-card strong {{
      display: inline-flex;
      min-height: 24px;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      margin-bottom: 8px;
    }}
    .takeaway-card p {{
      margin: 0;
      font-size: 14px;
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 5;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .takeaway-card span {{
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
    }}
    .section-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
    }}
    h2 {{
      margin: 0;
      font-size: 20px;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 16px 0 6px;
      font-size: 14px;
      color: var(--muted);
      letter-spacing: 0;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 3px 9px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
      white-space: nowrap;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .metric {{
      min-height: 96px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfc;
      overflow: hidden;
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
    }}
    .metric-value {{
      margin-top: 5px;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.15;
    }}
    .metric-note {{
      margin-top: 5px;
      color: var(--muted);
      font-size: 12px;
    }}
    .chart-board {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .chart-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      box-shadow: var(--shadow);
    }}
    .chart-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .chart-head a {{
      font-size: 12px;
    }}
    .chart-card img {{
      display: block;
      width: 100%;
      min-height: 120px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }}
    .chart-card p {{
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .insight-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      margin: 10px 0 12px;
    }}
    .insight-card {{
      border: 1px solid #d7e2e1;
      border-radius: 8px;
      background: #fbfdfd;
      padding: 12px;
    }}
    .insight-title {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .insight-signal {{
      margin-top: 3px;
      color: var(--ink);
      font-size: 17px;
      font-weight: 700;
    }}
    .insight-card dl {{
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 5px 8px;
      margin: 9px 0 0;
      font-size: 13px;
    }}
    .insight-card dt {{
      color: var(--muted);
      font-weight: 700;
    }}
    .insight-card dd {{
      margin: 0;
    }}
    .news-list {{
      display: grid;
      gap: 8px;
      padding-left: 0;
      list-style: none;
    }}
    .news-item {{
      border-left: 3px solid var(--accent);
      background: #f7faf9;
      padding: 9px 10px;
      border-radius: 6px;
      font-size: 14px;
    }}
    .review-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 8px;
    }}
    .review-card {{
      border: 1px solid #d7e2e1;
      border-radius: 8px;
      background: #fbfdfd;
      padding: 13px;
    }}
    .review-verdict {{
      display: inline-flex;
      min-height: 26px;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
      background: #eef4f4;
      color: #164c50;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .review-row {{
      display: grid;
      gap: 2px;
      margin-top: 8px;
    }}
    .review-row strong {{
      color: var(--muted);
      font-size: 12px;
    }}
    .review-row p {{
      margin: 0;
      font-size: 13px;
    }}
    .cross-check {{
      border-left: 4px solid var(--warn);
    }}
    .cross-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .cross-card {{
      border: 1px solid #e6dcc7;
      border-radius: 8px;
      background: #fffdf8;
      padding: 13px;
    }}
    .cross-top {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .cross-top strong {{
      font-size: 15px;
      line-height: 1.35;
    }}
    .cross-top span {{
      display: inline-flex;
      min-height: 24px;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
      background: #f3ead8;
      color: var(--warn);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .cross-card dl {{
      display: grid;
      grid-template-columns: 76px 1fr;
      gap: 6px 8px;
      margin: 0;
      font-size: 13px;
    }}
    .cross-card dt {{
      color: var(--muted);
      font-weight: 700;
    }}
    .cross-card dd {{
      margin: 0;
    }}
    .metric-up .metric-value {{ color: var(--up); }}
    .metric-down .metric-value {{ color: var(--down); }}
    .metric-gold .metric-value {{ color: var(--gold); }}
    ul {{
      margin: 8px 0 0;
      padding-left: 20px;
    }}
    .sources {{
      word-break: break-all;
      font-size: 13px;
    }}
    .source-scroll {{
      max-height: 112px;
      overflow: auto;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfc;
      padding: 8px 10px;
      overscroll-behavior: contain;
    }}
    .source-details {{
      margin-top: 6px;
    }}
    .source-details summary {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 30px;
      padding: 4px 10px;
      border: 1px solid rgba(15, 111, 115, 0.24);
      border-radius: 999px;
      background: #f4faf9;
      color: #164c50;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      user-select: none;
      list-style: none;
    }}
    .source-details summary::-webkit-details-marker {{
      display: none;
    }}
    .source-details summary::before {{
      content: "+";
      display: inline-grid;
      place-items: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--accent);
      color: #fff;
      font-size: 12px;
      line-height: 1;
    }}
    .source-details[open] summary::before {{
      content: "-";
    }}
    .source-details summary span {{
      color: var(--muted);
      font-weight: 600;
    }}
    .source-details[open] .source-scroll {{
      margin-top: 8px;
    }}
    .lead .source-scroll {{
      max-height: 58px;
      min-height: 34px;
      padding: 5px 8px;
    }}
    .lead .source-details {{
      margin-top: 0;
    }}
    .lead .source-details summary {{
      min-height: 24px;
      padding: 2px 8px;
      font-size: 11px;
    }}
    .lead .source-details summary::before {{
      width: 14px;
      height: 14px;
      font-size: 10px;
    }}
    .lead .sources {{
      font-size: 11px;
    }}
    a {{
      color: #155c8a;
    }}
    .disclaimer {{
      color: var(--muted);
      font-size: 13px;
      border-top: 1px solid var(--line);
      padding-top: 16px;
      margin-top: 20px;
    }}
    @media (max-width: 760px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .chart-board {{ grid-template-columns: 1fr; }}
      .review-grid {{ grid-template-columns: 1fr; }}
      .cross-grid {{ grid-template-columns: 1fr; }}
      .takeaways {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .lead .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      h1 {{ font-size: 25px; }}
      .section-head {{ flex-direction: column; }}
      .badge {{ align-self: flex-start; }}
    }}
    @media (max-width: 440px) {{
      .metrics {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap hero">
      <h1>{esc(payload.get("title", "경제 데일리 브리핑"))}</h1>
      <div class="meta">작성일 {esc(payload.get("report_date", ""))} · 생성시각 {esc(payload.get("generated_at", ""))} · 기준시간대 {esc(payload.get("timezone", ""))}</div>
      <nav class="topbar" aria-label="리포트 섹션">
        <a class="chip" href="#forecast">06:00 예측</a>
        <a class="chip" href="#comparison">07:00 비교</a>
        <a class="chip" href="#sections">섹션 분석</a>
        <a class="chip" href="#sources">출처</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="panel lead">
      <div class="section-head">
        <h2>{esc(payload["summary"].get("headline", ""))}</h2>
        <span class="badge">{esc(payload["summary"].get("stance", ""))}</span>
      </div>
      {render_metrics(payload["summary"].get("metrics", []))}
      <h3>출처 URL</h3>
      {render_source_urls(payload["summary"].get("source_urls", []))}
    </section>

    {key_takeaways}

    {render_charts(payload["summary"].get("charts", []))}

    {news_market_check}

    <div class="grid">
      <section class="panel" id="forecast">
        <div class="section-head">
          <h2>{esc(forecast.get("title", ""))}</h2>
          <span class="badge">0순위</span>
        </div>
        <h3>예측 근거</h3>
        {render_list(forecast.get("basis", []))}
        <h3>오늘의 판단 카드</h3>
        {render_insight_cards(forecast.get("insight_cards", []))}
        <details class="source-details forecast-raw"><summary>원문형 데이터 요약 <span>보기</span></summary><p>{esc(forecast.get("prediction", ""))}</p></details>
        <h3>체크포인트</h3>
        {render_list(forecast.get("watch_points", []))}
        <h3>출처 URL</h3>
        {render_source_urls(forecast.get("source_urls", []))}
      </section>

      <section class="panel" id="comparison">
        <div class="section-head">
          <h2>{esc(comparison.get("title", ""))}</h2>
          <span class="badge">{esc(comparison.get("status", ""))}</span>
        </div>
        <p>{esc(comparison.get("analysis", ""))}</p>
        <h3>변경 포인트</h3>
        {render_list(comparison.get("changed_points", []))}
        {render_review_items(comparison.get("review_items", []))}
        <h3>출처 URL</h3>
        {render_source_urls(comparison.get("source_urls", []))}
      </section>
    </div>

    <div id="sections">{sections}</div>

    <p class="disclaimer" id="sources">{esc(payload.get("disclaimer", ""))}</p>
  </main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(payload), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
