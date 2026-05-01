# Economy News Automation MVP

API 없이 공개 페이지와 브라우저 자동화로 웹 리포트를 만드는 경제 뉴스 자동화 초기안입니다.

## 채택 방향

- B안 우선: 웹 페이지/뉴스레터를 원본 산출물로 생성
- 인스타 카드뉴스는 웹 리포트 안정화 후 2단계에서 이미지로 변환
- 모든 주요 섹션에 출처 URL 표시
- 오전 6시 사전 예측 리포트 생성
- 오전 7시부터 신규 정보와 6시 예측을 비교해 1차 분석 생성
- API 키 없이 공개 RSS, 공개 CSV, 공개 웹 페이지, Playwright 브라우저 자동화 사용

## 실행

```powershell
python .\src\generate_report.py --input .\data\sample_daily_payload.json --output .\output\daily_report.html
```

생성 결과:

```text
output/daily_report.html
```

## 운영 스케줄 초안

| 시간 | 작업 |
|---|---|
| 06:00 | 전날/기존 누적 자료 기반 사전 예측 |
| 07:00 | 신규 뉴스와 예측 비교, 1차 분석 |
| 08:30 | 국내 장 시작 전 프리뷰 |
| 09:10 | 국장 초반 변동폭 반영 |
| 12:00 | 오전장 중간 점검 |
| 15:40 | 국장 마감 반영 |
| 16:00 | 부동산/정책/금 포함 최종 리포트 |
| 17:00 | 웹 링크/텔레그램/이메일 발송 |

## No API 수집 방식

- 뉴스: Google News RSS와 언론사/기관 RSS
- 미국장/금/환율: Stooq 공개 CSV 페이지
- 국내장: 네이버 금융 공개 페이지
- 부동산/정책: 국토교통부, 한국부동산원, KRX 공개 페이지를 Playwright로 방문
- 리포트: 수집 결과를 JSON으로 저장한 뒤 HTML 생성

## 실제 스냅샷 반영

API 키 없이 가능한 초기 데이터 수집입니다.

```powershell
python .\src\collect_stooq_snapshot.py --output .\data\market_snapshot.json
python .\src\collect_naver_market.py --output .\data\kr_market_snapshot.json
python .\src\collect_google_news_rss.py --config .\config\news_queries.json --output .\data\news_snapshot.json
python .\src\analyze_news.py --news .\data\news_snapshot.json --output .\data\news_analysis.json --recent-hours 36
python .\src\browser_collectors\public_page_probe.py --config .\config\public_pages.json --output .\data\public_page_probe.json
python .\src\browser_collectors\collect_rone_dashboard.py --output .\data\rone_dashboard.json
python .\src\browser_collectors\collect_molit_public_info.py --output .\data\molit_public_info.json
python .\src\build_actual_payload.py --base .\data\sample_daily_payload.json --snapshot .\data\market_snapshot.json --news-analysis .\data\news_analysis.json --kr-market .\data\kr_market_snapshot.json --page-probe .\data\public_page_probe.json --rone .\data\rone_dashboard.json --molit-info .\data\molit_public_info.json --output .\data\actual_daily_payload.json
python .\src\generate_report.py --input .\data\actual_daily_payload.json --output .\output\actual_daily_report.html
```

한 번에 실행하고 브라우저로 열기:

```powershell
.\run_no_api_pipeline.ps1
```

생성 결과:

```text
output/actual_daily_report.html
```

## Google Stitch 디자인 개선

Stitch에서 사용할 프롬프트는 `design/stitch_prompt.md`에 있습니다. Stitch가 만든 시안은 CSS와 레이아웃 참고용으로 사용하고, 데이터/출처 URL 렌더링 로직은 이 프로젝트에 유지합니다.

## GitHub Pages 배포

이 프로젝트는 GitHub Pages Actions 배포 구조를 포함합니다.

배포 후 자동 실행 시간:

| KST 기준 | UTC cron | 목적 |
|---|---|---|
| 06:00 | 21:00 전일 UTC | 오전 6시 사전 예측 리포트 |
| 07:00 | 22:00 전일 UTC | 오전 7시 비교 리포트 |
| 16:00 | 07:00 UTC | 장중/마감 후 업데이트 |

GitHub에 새 저장소를 만든 뒤 아래 명령을 실행합니다.

```powershell
git remote add origin https://github.com/<YOUR_ID>/<REPO_NAME>.git
git branch -M main
git push -u origin main
```

그 다음 GitHub 저장소에서:

1. `Settings` → `Pages`
2. `Build and deployment` → `Source`를 `GitHub Actions`로 선택
3. `Actions` 탭에서 `Build and Deploy Daily Economy Report` 실행 확인

배포 URL은 보통 아래 형식입니다.

```text
https://<YOUR_ID>.github.io/<REPO_NAME>/
```
