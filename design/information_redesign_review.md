# 정보전달 강화 재설계 검토

작성일: 2026-05-03

## 외부 사례에서 확인한 구조

### BlackRock Weekly Commentary

BlackRock은 리포트를 `Our bottom line`, `Market backdrop`, `Week ahead`, `Tactical granular views`로 나눈다. 핵심은 숫자 나열보다 먼저 “결론”을 짧게 제시하고, 그 다음 시장 배경과 앞으로 볼 이벤트를 붙이는 방식이다.

참고: https://www.blackrock.com/ch/professionals/en/insights/weekly-commentary

### J.P. Morgan Market Insights

J.P. Morgan의 Market Insights는 시장과 경제의 변화, 투자자에게 주는 의미, 차트 기반 설명을 같이 제공한다. 특히 Guide to the Markets는 차트와 말할 포인트를 결합하는 방식이 강하다.

참고: https://am.jpmorgan.com/us/en/asset-management/liq/insights/market-insights/market-updates/

### Morning Brew형 데일리 브리핑

Morning Brew 스타일은 시장 가격표를 먼저 보여주고, 이어서 “왜 움직였는지”, “무엇을 봐야 하는지”를 짧게 연결한다. 빠르게 읽는 사용자를 위해 섹션 제목과 짧은 문장 리듬이 중요하다.

참고: https://journal.businesstoday.org/bt-online/2017/5/29/the-morning-brew

## 현재 리포트의 문제

1. 실제 데이터는 들어오지만, 사용자가 바로 판단할 수 있는 구조가 약하다.
2. 오전 6시 사전 예측이 한 문단으로 합쳐져 있어 시장 신호가 섞인다.
3. 미국장 섹션이 지수 숫자에 머물러 있고, 강한 지수/약한 지수/한국장 연결이 부족하다.
4. 오전 7시 비교 분석은 아직 6시 데이터와 7시 데이터를 별도로 저장하지 않아 실제 비교라고 보기 어렵다.
5. 차트가 없어 숫자의 방향성을 시각적으로 확인하기 어렵다.

## 재설계 원칙

### 1. 데이터 수집과 해석을 분리

각 섹션은 아래 순서를 따른다.

```text
숫자 → 신호 → 근거 → 시사점 → 확인할 것
```

### 2. 오전 6시는 예측문이 아니라 판단 카드

기존:

```text
미국장, 국내장, 금, 환율을 한 문단으로 연결
```

변경:

```text
1. 미국장이 남긴 신호
2. 국내장이 확인해야 할 것
3. 리스크 변수
```

각 카드는 `신호`, `근거`, `시사점`, `확인할 것`을 가진다.

### 3. 오전 7시는 아직 비워둔다

현재는 6시와 7시 데이터를 별도 히스토리로 저장하지 않는다. 따라서 7시 영역은 “반영 예정”으로 명확히 표시한다. 이후 구현할 때는 `forecast_0600.json`과 `comparison_0700.json`을 따로 저장해 진짜 비교를 만든다.

### 4. 미국장은 디테일을 추가

미국장 섹션은 단순 수익률이 아니라 아래를 보여준다.

- 가장 강한 지수
- 가장 약한 지수
- 세 지수의 동반성
- 금/환율과의 동조 여부
- 한국장 연결 포인트

### 5. 차트는 우선 국내장부터 삽입

API 없이 안정적으로 붙일 수 있는 공개 차트는 네이버 금융 KOSPI/KOSDAQ 이미지다.

- KOSPI: https://ssl.pstatic.net/imgfinance/chart/sise/siseMainKOSPI.png
- KOSDAQ: https://ssl.pstatic.net/imgfinance/chart/sise/siseMainKOSDAQ.png

미국장 차트는 공개 이미지 URL 안정성이 낮아, 다음 단계에서 자체 SVG 차트 또는 다른 공개 차트 소스 검토가 필요하다.

## 이번 반영 사항

1. 상단 실제 스냅샷 아래에 KOSPI/KOSDAQ 차트 보드 추가
2. 오전 6시 사전 예측을 카드형 구조로 변경
3. 오전 7시 비교 분석은 `반영 예정`으로 명확히 표시
4. 미국장 섹션에 `지수 강도`, `해석 순서`, `금/환율`, `한국장 연결` 항목 추가
5. 원문형 긴 데이터 요약은 접힌 영역으로 이동

## 다음 단계

1. 6시/7시/16시 결과를 날짜별 JSON으로 저장
2. 7시에는 6시 예측 대비 신규 뉴스/시장 수치 변화만 비교
3. 미국장 차트를 자체 SVG로 생성하거나 안정적인 공개 차트 소스를 확보
4. 국내장 업종/수급 데이터를 추가해 한국장 인사이트 강화
5. 부동산 섹션도 가격, 거래, 미분양, 정책의 4칸 구조로 재배치
