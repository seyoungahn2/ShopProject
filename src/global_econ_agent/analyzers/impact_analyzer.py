import json
import logging

from openai import OpenAI

from global_econ_agent.config import Settings, get_settings
from global_econ_agent.models.schemas import (
    Article,
    Category,
    ImpactAnalysis,
    ImpactLevel,
    Region,
    Scenario,
    TermGlossary,
)
from global_econ_agent.utils.glossary import extract_glossary, merge_glossaries
from global_econ_agent.utils.labels import category_label

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 미국, 한국, 일본 주식·채권 시장에 특화된 글로벌 매크로 애널리스트입니다.

## 작성 규칙 (필수)
1. 모든 분석 내용은 **한국어**로 작성합니다.
2. 고유명사·전문 용어·지수명·기관명은 **원어 그대로** 쓰되, 본문에서는 한국어 설명을 우선합니다.
   예: "연준이(Fed) 기준금리를 동결했다"
3. 사용한 원어 용어는 `term_glossary`에 반드시 포함하고, 각 항목에 **한글 해석**을 달아주세요.
   예: {"term": "FOMC", "meaning_ko": "연방공개시장위원회 — 미국 금리를 결정하는 기구"}
4. 뉴스 제목은 `title_ko`에 한국어로 번역·요약하고, `title_original`에 원문을 보존합니다.
5. 반드시 요청된 JSON 형식으로만 응답하세요."""


class ImpactAnalyzer:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = self.settings.openai_model
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY required for AI analysis")
            self._client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
        return self._client

    def analyze_articles(self, articles: list[Article], top_n: int = 15) -> list[ImpactAnalysis]:
        if not self.settings.openai_api_key:
            logger.warning("OPENAI_API_KEY 미설정 — 규칙 기반 분석으로 대체")
            return self._fallback_analysis(articles, top_n)

        key_articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)[:top_n]
        analyses: list[ImpactAnalysis] = []

        batch_size = 5
        for i in range(0, len(key_articles), batch_size):
            batch = key_articles[i : i + batch_size]
            try:
                batch_results = self._analyze_batch(batch)
                analyses.extend(batch_results)
            except Exception as e:
                logger.error("AI 분석 실패 (배치 %d): %s", i // batch_size, e)
                analyses.extend(self._fallback_analysis(batch, len(batch)))

        return analyses

    def _analyze_batch(self, articles: list[Article]) -> list[ImpactAnalysis]:
        articles_text = "\n\n".join(
            f"[{i+1}] 원문 제목: {a.title}\n요약: {a.summary or '없음'}\n"
            f"출처: {a.source_name} | 지역: {a.region.value} | "
            f"카테고리: {', '.join(category_label(c) for c in a.categories)}"
            for i, a in enumerate(articles)
        )

        prompt = f"""다음 뉴스 기사들의 시장 영향을 분석하세요. 모든 설명은 한국어로 작성하세요.

{articles_text}

JSON 형식으로 응답:
{{
  "analyses": [
    {{
      "article_index": 1,
      "title_ko": "한국어 제목 (원문을 번역·요약)",
      "title_original": "원문 제목",
      "impact_level": "high|medium|low",
      "regions_affected": ["US", "KR", "JP", "GLOBAL"],
      "stock_impact": "주식 시장 영향 (한국어, 구체적 섹터/지수 포함)",
      "bond_impact": "채권 시장 영향 (한국어)",
      "rate_outlook": "금리 전망 영향 (한국어)",
      "affected_sectors": ["섹터1", "섹터2"],
      "affected_companies": ["기업1", "기업2"],
      "summary_ko": "핵심 요약 2-3문장 (한국어)",
      "term_glossary": [
        {{"term": "Fed", "meaning_ko": "연방준비제도 — 미국 중앙은행"}}
      ]
    }}
  ]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return self._parse_batch_response(content, articles)

    def _parse_batch_response(self, content: str, articles: list[Article]) -> list[ImpactAnalysis]:
        try:
            data = json.loads(content)
            items = data if isinstance(data, list) else data.get("analyses", data.get("results", []))
        except json.JSONDecodeError:
            logger.error("JSON 파싱 실패: %s", content[:200])
            return self._fallback_analysis(articles, len(articles))

        analyses: list[ImpactAnalysis] = []
        for item in items:
            idx = item.get("article_index", 1) - 1
            if 0 <= idx < len(articles):
                article = articles[idx]
                regions = []
                for r in item.get("regions_affected", []):
                    try:
                        regions.append(Region(r))
                    except ValueError:
                        pass

                try:
                    level = ImpactLevel(item.get("impact_level", "medium"))
                except ValueError:
                    level = ImpactLevel.MEDIUM

                glossary = [
                    TermGlossary(**g) for g in item.get("term_glossary", [])
                    if g.get("term") and g.get("meaning_ko")
                ]
                # AI가 누락한 용어는 자동 추출로 보완
                combined_text = " ".join([
                    item.get("title_ko", ""),
                    item.get("summary_ko", ""),
                    item.get("stock_impact", ""),
                    item.get("bond_impact", ""),
                    article.title,
                ])
                glossary = merge_glossaries(glossary, extract_glossary(combined_text))

                analyses.append(
                    ImpactAnalysis(
                        article_id=article.id or "",
                        title_ko=item.get("title_ko") or article.title,
                        title_original=item.get("title_original") or article.title,
                        categories=article.categories,
                        regions_affected=regions or [article.region],
                        impact_level=level,
                        stock_impact=item.get("stock_impact", ""),
                        bond_impact=item.get("bond_impact", ""),
                        rate_outlook=item.get("rate_outlook", ""),
                        affected_sectors=item.get("affected_sectors", []),
                        affected_companies=item.get("affected_companies", []),
                        summary_ko=item.get("summary_ko", ""),
                        term_glossary=glossary,
                    )
                )

        return analyses

    def _fallback_analysis(self, articles: list[Article], top_n: int) -> list[ImpactAnalysis]:
        analyses: list[ImpactAnalysis] = []
        for article in articles[:top_n]:
            level = ImpactLevel.HIGH if article.relevance_score >= 5 else ImpactLevel.MEDIUM
            if article.relevance_score < 2:
                level = ImpactLevel.LOW

            stock_impact = _category_stock_hint(article.categories)
            bond_impact = _category_bond_hint(article.categories)
            rate_outlook = _category_rate_hint(article.categories)
            cats = ", ".join(category_label(c) for c in article.categories)

            combined = f"{article.title} {article.summary}"
            glossary = extract_glossary(combined)
            title_ko = _fallback_title_ko(article)

            analyses.append(
                ImpactAnalysis(
                    article_id=article.id or "",
                    title_ko=title_ko,
                    title_original=article.title,
                    categories=article.categories,
                    regions_affected=[article.region],
                    impact_level=level,
                    stock_impact=stock_impact,
                    bond_impact=bond_impact,
                    rate_outlook=rate_outlook,
                    affected_sectors=[],
                    affected_companies=[],
                    summary_ko=(
                        f"[자동 분류] {cats} 관련 이슈로 분류되었습니다. "
                        f"원문: {article.title}"
                    ),
                    term_glossary=glossary,
                )
            )
        return analyses


class ScenarioGenerator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = self.settings.openai_model
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY required for scenario generation")
            self._client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
        return self._client

    def generate(
        self,
        analyses: list[ImpactAnalysis],
        scenario_count: int = 3,
    ) -> tuple[str, list[Scenario], list[TermGlossary]]:
        if not self.settings.openai_api_key:
            return self._fallback_scenarios(analyses)

        issues_summary = "\n".join(
            f"- [{a.impact_level.value}] {a.title_ko}: {a.summary_ko}"
            for a in analyses[:15]
        )

        prompt = f"""오늘의 주요 글로벌 경제 이슈를 바탕으로 투자 시나리오를 작성하세요.
모든 내용은 한국어로 작성하고, 원어 용어는 term_glossary에 해석을 달아주세요.

## 주요 이슈
{issues_summary}

## 요청
1. 경영진 요약 (executive_summary): 3-5문장, 한국어
2. {scenario_count}개 시나리오 (낙관/기준/비관)
3. 보고서 전체 용어집 (term_glossary)

JSON 형식:
{{
  "executive_summary": "한국어 요약",
  "term_glossary": [
    {{"term": "S&P 500", "meaning_ko": "미국 대형주 500개 종목 지수"}}
  ],
  "scenarios": [
    {{
      "name": "시나리오명 (한국어)",
      "probability": "30%",
      "description": "상세 설명 (한국어)",
      "triggers": ["촉발 요인1"],
      "us_market_outlook": "미국 시장 전망 (한국어, S&P 500/NASDAQ/美채 언급)",
      "kr_market_outlook": "한국 시장 전망 (한국어, KOSPI/한국채 언급)",
      "jp_market_outlook": "일본 시장 전망 (한국어, 닛케이/JGB 언급)",
      "rate_outlook": "금리 전망 (한국어)",
      "key_risks": ["리스크1"],
      "investment_implications": "투자 시사점 (한국어)",
      "term_glossary": []
    }}
  ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            executive_summary = data.get("executive_summary", "")
            report_glossary = [
                TermGlossary(**g) for g in data.get("term_glossary", [])
                if g.get("term") and g.get("meaning_ko")
            ]

            scenarios: list[Scenario] = []
            for s in data.get("scenarios", [])[:scenario_count]:
                scenario_glossary = [
                    TermGlossary(**g) for g in s.get("term_glossary", [])
                    if g.get("term") and g.get("meaning_ko")
                ]
                scenario_data = {k: v for k, v in s.items() if k != "term_glossary"}
                scenario = Scenario(**scenario_data, term_glossary=scenario_glossary)
                scenarios.append(scenario)

            # 이슈별 용어집 + 시나리오 용어집 통합
            issue_glossaries = [a.term_glossary for a in analyses]
            scenario_glossaries = [s.term_glossary for s in scenarios]
            all_glossary = merge_glossaries(report_glossary, *issue_glossaries, *scenario_glossaries)
            all_glossary = merge_glossaries(
                all_glossary,
                extract_glossary(executive_summary + " ".join(s.description for s in scenarios)),
            )

            return executive_summary, scenarios, all_glossary

        except Exception as e:
            logger.error("시나리오 생성 실패: %s", e)
            return self._fallback_scenarios(analyses)

    def _fallback_scenarios(
        self, analyses: list[ImpactAnalysis]
    ) -> tuple[str, list[Scenario], list[TermGlossary]]:
        high_impact = [a for a in analyses if a.impact_level == ImpactLevel.HIGH]
        summary = (
            f"오늘 {len(analyses)}건의 주요 이슈가 분석되었습니다. "
            f"그 중 영향도가 높은 이슈 {len(high_impact)}건이 확인되었습니다. "
            "OPENAI_API_KEY 설정 시 AI 기반 상세 시나리오와 용어 해석이 생성됩니다."
        )

        scenarios = [
            Scenario(
                name="기준 시나리오",
                probability="50%",
                description="현재 거시경제 추세가 대체로 유지되는 상황",
                triggers=["주요 중앙은행 기준금리 동결"],
                us_market_outlook="변동성 확대 속 박스권 — S&P 500·NASDAQ 횡보",
                kr_market_outlook="외국인 수급에 따른 등락 — KOSPI 박스권",
                jp_market_outlook="엔화 약세(円安) 지속 시 수출주 우위 — 닛케이 보합",
                rate_outlook="고금리 장기화 기조 유지",
                key_risks=["지정학 리스크", "인플레이션 재부상"],
                investment_implications="분산 투자 및 헤지 유지 권고",
                term_glossary=extract_glossary("S&P 500 NASDAQ KOSPI Nikkei"),
            ),
            Scenario(
                name="낙관 시나리오",
                probability="25%",
                description="인플레이션 둔화 및 금리 인하(rate cut) 기대",
                triggers=["연준(Fed) 비둘기파(dovish) 전환", "무역 긴장 완화"],
                us_market_outlook="성장주·기술주 랠리 — NASDAQ 강세",
                kr_market_outlook="외국인 순매수 전환, 반도체 강세 — KOSPI 상승",
                jp_market_outlook="약엔(円安) 수혜 지속 — 수출주 강세",
                rate_outlook="금리 인하 사이클 진입 기대",
                key_risks=["금리 인하 시점 지연"],
                investment_implications="성장주·채권 비중 확대 검토",
                term_glossary=extract_glossary("Fed dovish rate cut NASDAQ"),
            ),
            Scenario(
                name="비관 시나리오",
                probability="25%",
                description="지정학 충격 및 경기 침체(recession) 우려",
                triggers=["지정학 분쟁 확대", "유가(oil) 급등"],
                us_market_outlook="안전자산(safe haven) 선호, 주식 조정",
                kr_market_outlook="환율 부담, 수출주 압박 — KOSPI 하락",
                jp_market_outlook="엔화 급등(円高) 시 수출주 타격 — 닛케이 약세",
                rate_outlook="스태그플레이션(stagflation) 우려",
                key_risks=["공급망 차질", "에너지 쇼크"],
                investment_implications="현금·금·단기채 비중 확대",
                term_glossary=extract_glossary("recession safe haven stagflation oil"),
            ),
        ]

        all_glossary = merge_glossaries(
            *[a.term_glossary for a in analyses],
            *[s.term_glossary for s in scenarios],
            extract_glossary(summary),
        )
        return summary, scenarios, all_glossary


def _fallback_title_ko(article: Article) -> str:
    """원문 제목이 이미 한국어이면 그대로, 영어면 원문 표기 + 자동 분류 안내."""
    # 한글 문자 비율로 판단
    korean_chars = sum(1 for c in article.title if "\uac00" <= c <= "\ud7a3")
    if korean_chars > len(article.title) * 0.3:
        return article.title
    cats = ", ".join(category_label(c) for c in article.categories)
    return f"[{cats}] {article.title}"


def _category_stock_hint(categories: list[Category]) -> str:
    hints = {
        Category.INTEREST_RATES: "금리 민감 섹터(금융, 부동산, 성장주) 변동성 확대",
        Category.CONFLICT: "방산·에너지 강세, 위험회피(risk-off) 시 전반적 약세",
        Category.COMMODITIES: "원자재·에너지 관련주 강세, 비용 부담 업종 약세",
        Category.FX: "수출주·해외 매출 비중 높은 기업 환차익 영향",
        Category.TRADE: "수출 의존 기업 및 관세(tariff) 영향 업종 주목",
        Category.CORPORATE: "해당 기업 및 동종 업종 주가 변동",
        Category.ECONOMY: "경기 민감주 전반 영향",
    }
    for cat in categories:
        if cat in hints:
            return hints[cat]
    return "시장 전반에 제한적 영향 예상"


def _category_bond_hint(categories: list[Category]) -> str:
    if Category.INTEREST_RATES in categories:
        return "국채 금리(yield) 변동성 확대, 듀레이션(duration) 리스크 주의"
    if Category.CONFLICT in categories or Category.TERRORISM in categories:
        return "안전자산(safe haven) 수요 증가, 국채 가격 상승(금리 하락) 가능"
    return "채권 시장 영향 제한적"


def _category_rate_hint(categories: list[Category]) -> str:
    if Category.INTEREST_RATES in categories:
        return "중앙은행 정책 방향에 따른 금리 재가격 가능"
    if Category.ECONOMY in categories:
        return "경기 지표에 따른 금리 기대 조정"
    return "현 수준 유지 가능성"
