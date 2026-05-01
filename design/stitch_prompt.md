# Google Stitch 디자인 프롬프트

아래 프롬프트를 Google Stitch에 넣어 웹 리포트 디자인 시안을 만들고, 결과 코드/CSS를 현재 `src/generate_report.py` 템플릿에 반영한다.

```text
Design a mobile-first Korean financial intelligence web report for daily economy briefings.

The product is not a marketing landing page. It is a dense but elegant operational dashboard for investors and analysts.

Primary user goal:
- Read a 6:00 AM forecast based on yesterday and historical data.
- Compare it with 7:00 AM fresh news and market data.
- Review US market, Korean market, gold, Korean real estate, and real estate policy sections.
- Every analytical claim must show source URLs.

Visual direction:
- Calm institutional finance tone.
- White and light gray background.
- Use restrained teal for primary emphasis.
- Use red for up/risk-on, blue for down/risk-off, amber for gold.
- Avoid purple gradients, decorative blobs, oversized hero sections, and nested cards.
- Use compact cards only for metrics.

Required layout:
1. Header with report title, date, generated time, timezone.
2. Sticky or top summary section with market stance and key metrics.
3. Two-column desktop grid:
   - 6:00 AM forecast.
   - 7:00 AM comparison analysis.
4. Full-width sections:
   - Fresh news.
   - US market.
   - Korean market.
   - Gold.
   - Korean real estate.
   - Real estate policy comparison.
5. Each section has:
   - status badge.
   - concise analysis paragraph.
   - metric cards if available.
   - source URL list.

Responsive behavior:
- Desktop width max 1080px.
- Mobile single column.
- Text must never overflow cards or buttons.
- Metric cards keep stable height.

Typography:
- Korean-first sans-serif.
- Clear hierarchy, no negative letter spacing.
- Compact dashboard headings, not hero-scale type inside panels.
```

## 적용 방식

1. Stitch에서 위 프롬프트로 시안 생성
2. 가장 마음에 드는 화면의 HTML/CSS 또는 스크린샷 확보
3. 현재 템플릿에 색상, 간격, 섹션 구성만 반영
4. 데이터 구조와 출처 URL 렌더링 로직은 유지
