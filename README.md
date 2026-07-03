# Global Econ Intelligence Agent

미국·한국·일본 주식 및 채권 투자를 위한 **글로벌 경제 인텔리전스 AI 에이전트**입니다.

매일 글로벌 뉴스를 자동 수집하고, 핵심 이슈를 분석하여 기업·주가·금리에 미치는 영향과 미래 시나리오 보고서를 생성합니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| **뉴스 수집** | RSS 피드 + NewsAPI로 미국/한국/일본/글로벌 경제 뉴스 자동 수집 |
| **이슈 분류** | 정치, 경제, 금리, 전쟁, 원자재, 환율, 무역, 재난, 테러 등 10개 카테고리 |
| **영향 분석** | AI가 주식·채권·금리 전망 및 관련 섹터/기업 영향 분석 |
| **시나리오 보고서** | 낙관/기준/비관 시나리오와 투자 시사점 자동 생성 |
| **한글 보고서** | 본문은 한국어, 원어 용어는 해석 병기 |
| **다양한 저장 형식** | Markdown, Excel, CSV, Google Sheets |
| **일일 스케줄** | 매일 지정 시각에 자동 실행 (cron/APScheduler) |

## 커버리지

### 지역
- 🇺🇸 **미국** — S&P 500, NASDAQ, 미국 국채, 연준(Fed)
- 🇰🇷 **한국** — KOSPI, KOSDAQ, 한국 국채, 한국은행
- 🇯🇵 **일본** — 닛케이 225, TOPIX, 일본 국채, BOJ

### 이슈 카테고리
정치 · 경제 · 금리 · 전쟁/분쟁 · 원자재 · 환율 · 무역 · 재난/재해 · 테러/안보 · 기업/주가

## 빠른 시작

### 1. 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 환경 설정

```bash
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 설정 (필수 — AI 분석용)
# NEWSAPI_KEY 설정 (선택 — 추가 뉴스 소스)
```

### 3. 실행

```bash
# 전체 파이프라인 (수집 → 분석 → 보고서)
global-econ run

# 뉴스 수집만
global-econ collect

# 저장된 기사 기반 분석만
global-econ analyze

# 에이전트 상태 확인
global-econ status

# 매일 자동 실행 스케줄러
global-econ schedule
```

### 4. 보고서 확인

실행 후 `reports/` 폴더에 아래 형식으로 저장됩니다.

| 형식 | 파일 | 용도 |
|------|------|------|
| **Markdown** | `report_YYYY-MM-DD.md` | 읽기 편한 한글 보고서 |
| **Excel** | `report_YYYY-MM-DD.xlsx` | 시트별 정리 (요약/핵심이슈/시나리오/용어해석) |
| **CSV** | `report_YYYY-MM-DD.csv` | 구글 시트 가져오기에 적합 |

### 5. 구글 드라이브 / 스프레드시트 연동

**방법 A — Excel/CSV 업로드 (가장 간단)**

1. `global-econ run` 실행
2. `reports/report_YYYY-MM-DD.xlsx` 또는 `.csv`를 구글 드라이브에 업로드
3. "Google 스프레드시트로 열기" 선택

**방법 B — Google Sheets 자동 업로드**

```bash
pip install -e ".[google]"
```

1. [Google Cloud Console](https://console.cloud.google.com/)에서 서비스 계정 생성
2. Google Sheets API + Drive API 활성화
3. JSON 키를 `credentials/google-service-account.json`에 저장
4. 구글 스프레드시트를 만들고 서비스 계정 이메일을 **편집자**로 공유
5. `.env` 설정:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/google-service-account.json
GOOGLE_SPREADSHEET_ID=스프레드시트_ID
```

이후 `global-econ run` 시 날짜별 시트가 자동으로 추가됩니다.

## 보고서 언어 규칙

- **본문**: 모두 한국어
- **원어 용어**: Fed, FOMC, KOSPI 등은 원문 유지
- **용어 해석**: 각 이슈·시나리오·보고서 말미에 `원어 → 한글 해석` 자동 병기

예시:
```
연준(Fed)이 FOMC 회의에서 금리를 동결했습니다.

용어 해석:
- Fed: 연방준비제도 — 미국 중앙은행
- FOMC: 연방공개시장위원회 — 미국 금리를 결정하는 기구
```

## 아키텍처

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  Collectors │───▶│  Processors  │───▶│  Analyzers  │───▶│   Reporter   │
│  RSS/NewsAPI│    │ Classify/Dedup│    │ Impact/Scene│    │ MD/XLSX/CSV  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
       │                  │                   │                   │
       └──────────────────┴───────────────────┴───────────────────┘
                                    │
                              ┌─────▼─────┐
                              │  SQLite   │
                              │    DB     │
                              └───────────┘
```

## 뉴스 소스 설정

`config/news_sources.yaml`에서 RSS 피드와 NewsAPI 쿼리를 관리합니다.

```yaml
sources:
  - id: reuters_business
    name: "Reuters Business"
    region: US
    type: rss
    url: "https://feeds.reuters.com/reuters/businessNews"
    enabled: true
```

소스 추가/비활성화는 `enabled: false`로 간단히 제어할 수 있습니다.

## Cron / Systemd 자동화

### Cron 예시 (매일 오전 7시 KST)

```cron
0 7 * * * /path/to/global-econ-agent/scripts/run_daily.sh >> /var/log/global-econ.log 2>&1
```

### Docker (선택)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["global-econ", "schedule"]
```

## 프로젝트 구조

```
global-econ-agent/
├── config/
│   ├── settings.yaml          # 에이전트 설정
│   └── news_sources.yaml      # 뉴스 소스
├── src/global_econ_agent/
│   ├── collectors/            # RSS, NewsAPI 수집기
│   ├── processors/            # 분류, 중복 제거
│   ├── analyzers/             # AI 영향 분석, 시나리오 생성
│   ├── reporters/             # Markdown 보고서
│   ├── storage/               # SQLite DB
│   ├── scheduler/             # 일일 스케줄러
│   ├── agent.py               # 오케스트레이터
│   └── main.py                # CLI
├── reports/                   # 생성된 보고서
├── data/                      # DB 및 캐시
└── scripts/run_daily.sh       # cron용 스크립트
```

## API 키 안내

| 서비스 | 용도 | 필수 여부 |
|--------|------|-----------|
| OpenAI API | 이슈 영향 분석, 시나리오 생성 | **권장** (미설정 시 규칙 기반 대체) |
| NewsAPI | 추가 뉴스 검색 | 선택 |

OpenAI 호환 API (Azure OpenAI, Local LLM 등)도 `OPENAI_BASE_URL` 설정으로 사용 가능합니다.

## 면책 조항

본 에이전트가 생성하는 보고서는 공개 뉴스를 기반으로 한 **참고 자료**이며, 투자 권유가 아닙니다. 투자 결정은 반드시 전문가 상담과 추가 검증을 거쳐 주세요.

## 라이선스

MIT
