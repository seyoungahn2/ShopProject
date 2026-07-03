import json
import logging
from collections import defaultdict

from openai import OpenAI

from global_econ_agent.config import Settings, get_settings
from global_econ_agent.models.schemas import (
    DailyReport,
    ImpactAnalysis,
    ImpactLevel,
    Region,
    ResearchReportSections,
    Scenario,
)
from global_econ_agent.utils.labels import category_label, impact_label, region_label

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """당신은 글로벌 투자은행(IB)의 수석 매크로 전략가입니다.
미국, 한국, 일본 주식·채권·환율·금리 시장을 아우르는 **전문 리서치 보고서**를 작성합니다.

## 작성 규칙 (필수)
1. 증권사 리서치 보고서처럼 **서술형 문체**로 작성합니다. 표나 이모지는 사용하지 않습니다.
2. 모든 본문은 **한국어**로 작성하되, Fed, FOMC, KOSPI 등 전문 용어는 원어를 유지합니다.
3. 각 섹션은 최소 2~4문단의 완결된 분석 글로 작성합니다.
4. 데이터·사실과 해석·전망을 명확히 구분합니다.
5. 투자 권유가 아닌 분석·전망임을 전문적으로 서술합니다.
6. 반드시 요청된 JSON 형식으로만 응답하세요."""


class ResearchReportComposer:
    """구조화된 분석 데이터를 전문 리서치 보고서 서술형 본문으로 변환."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = self.settings.openai_model
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY required")
            self._client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
        return self._client

    def compose(
        self,
        report_date: str,
        executive_summary: str,
        key_issues: list[ImpactAnalysis],
        scenarios: list[Scenario],
        articles_collected: int,
    ) -> ResearchReportSections:
        if self.settings.openai_api_key:
            try:
                return self._compose_with_llm(
                    report_date, executive_summary, key_issues, scenarios, articles_collected
                )
            except Exception as e:
                logger.error("리서치 보고서 AI 작성 실패: %s", e)

        return self._compose_fallback(
            report_date, executive_summary, key_issues, scenarios, articles_collected
        )

    def _compose_with_llm(
        self,
        report_date: str,
        executive_summary: str,
        key_issues: list[ImpactAnalysis],
        scenarios: list[Scenario],
        articles_collected: int,
    ) -> ResearchReportSections:
        issues_text = "\n".join(
            f"- [{impact_label(i.impact_level)}] {i.title_ko}: {i.summary_ko} "
            f"(주식: {i.stock_impact} / 채권: {i.bond_impact} / 금리: {i.rate_outlook})"
            for i in key_issues[:12]
        )
        scenarios_text = "\n".join(
            f"- {s.name} ({s.probability}): {s.description}"
            for s in scenarios
        )

        prompt = f"""다음 분석 데이터를 바탕으로 **전문 리서치 보고서** 본문을 작성하세요.
증권사 Daily Strategy Note / Macro Outlook 형식으로, 서술형 문단으로 작성합니다.

보고서 일자: {report_date}
수집 기사: {articles_collected}건 | 분석 이슈: {len(key_issues)}건

## 기존 요약
{executive_summary}

## 핵심 이슈
{issues_text}

## 시나리오
{scenarios_text}

JSON 형식:
{{
  "report_title": "글로벌 매크로 & 멀티에셋 투자 리서치",
  "subtitle": "Daily Strategy Note",
  "investment_summary": "투자 요약 2-3문단",
  "key_takeaways": ["핵심 시사점 1 (완전한 문장)", "핵심 시사점 2", "핵심 시사점 3", "핵심 시사점 4", "핵심 시사점 5"],
  "macro_overview": "거시경제 환경 분석 2-4문단",
  "us_analysis": "미국 시장 분석 2-3문단 (S&P 500, NASDAQ, Fed, 미국채)",
  "kr_analysis": "한국 시장 분석 2-3문단 (KOSPI, KOSDAQ, 한국은행, 원화)",
  "jp_analysis": "일본 시장 분석 2-3문단 (닛케이, BOJ, 엔화)",
  "equity_outlook": "주식시장 전망 2-3문단",
  "bond_outlook": "채권시장 전망 2-3문단",
  "fx_outlook": "환율 전망 2-3문단",
  "rate_outlook_section": "금리 전망 2-3문단",
  "thematic_analysis": "주요 테마별 심층 분석 3-5문단 (금리, 지정학, 무역, 원자재 등 이슈를 통합 서술)",
  "scenario_analysis": "시나리오별 전망 서술 3-4문단",
  "risk_assessment": "리스크 요인 분석 2-3문단",
  "investment_strategy": "투자 전략 및 포지셔닝 시사점 2-3문단",
  "conclusion": "결론 1-2문단"
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return ResearchReportSections(**data)

    def _compose_fallback(
        self,
        report_date: str,
        executive_summary: str,
        key_issues: list[ImpactAnalysis],
        scenarios: list[Scenario],
        articles_collected: int,
    ) -> ResearchReportSections:
        """LLM 없이도 전문 리서치 형식의 서술형 보고서 생성."""
        by_region: dict[Region, list[ImpactAnalysis]] = defaultdict(list)
        for issue in key_issues:
            for region in issue.regions_affected:
                by_region[region].append(issue)

        high_issues = [i for i in key_issues if i.impact_level == ImpactLevel.HIGH]

        takeaways = []
        for issue in key_issues[:5]:
            summary = _clean_summary(issue.summary_ko)
            takeaways.append(
                f"{_clean_title(issue.title_ko)} "
                f"{summary} "
                f"이 이슈는 {', '.join(region_label(r) for r in issue.regions_affected)} 시장에 "
                f"{impact_label(issue.impact_level)} 수준의 영향을 미칠 것으로 판단됩니다."
            )

        macro = (
            f"본 보고서 작성일({report_date}) 기준, 글로벌 경제·금융 시장을 둘러싼 주요 변수들이 "
            f"동시다발적으로 작용하고 있습니다. 당일 공개 뉴스 {articles_collected}건을 수집·분석한 결과, "
            f"핵심 모니터링 이슈는 {len(key_issues)}건으로 추출되었으며, "
            f"이 중 영향도가 높은 이슈는 {len(high_issues)}건입니다.\n\n"
            f"{executive_summary}\n\n"
            "거시경제 측면에서 중앙은행 정책 기조, 지정학적 리스크, 환율 변동, 원자재 가격이 "
            "미국·한국·일본 자산시장의 방향성을 동시에 좌우하는 핵심 축으로 작용하고 있습니다. "
            "특히 금리 경로에 대한 시장의 기대와 실제 경제지표 간의 괴리가 "
            "단기 변동성을 확대시키는 요인으로 부각되고 있습니다."
        )

        return ResearchReportSections(
            report_title="글로벌 매크로 & 멀티에셋 투자 리서치",
            subtitle="Daily Strategy Note",
            investment_summary=_build_investment_summary(report_date, key_issues, scenarios),
            key_takeaways=takeaways,
            macro_overview=macro,
            us_analysis=_build_regional_analysis(Region.US, by_region.get(Region.US, []), key_issues),
            kr_analysis=_build_regional_analysis(Region.KR, by_region.get(Region.KR, []), key_issues),
            jp_analysis=_build_regional_analysis(Region.JP, by_region.get(Region.JP, []), key_issues),
            equity_outlook=_build_asset_outlook("주식", key_issues, "stock_impact"),
            bond_outlook=_build_asset_outlook("채권", key_issues, "bond_impact"),
            fx_outlook=_build_fx_outlook(key_issues),
            rate_outlook_section=_build_asset_outlook("금리", key_issues, "rate_outlook"),
            thematic_analysis=_build_thematic_analysis(key_issues),
            scenario_analysis=_build_scenario_narrative(scenarios),
            risk_assessment=_build_risk_assessment(key_issues, scenarios),
            investment_strategy=_build_investment_strategy(scenarios),
            conclusion=_build_conclusion(report_date, key_issues),
        )


def _build_investment_summary(
    report_date: str,
    issues: list[ImpactAnalysis],
    scenarios: list[Scenario],
) -> str:
    top = issues[:3]
    issue_refs = " ".join(f"「{_clean_title(i.title_ko)}」" for i in top)
    base = (
        f"{report_date} 발행 Daily Strategy Note에서는, "
        f"미국·한국·일본 멀티에셋 시장을 대상으로 당일 핵심 변수를 점검합니다. "
        f"금일 시장을 지배하는 주요 이슈로는 {issue_refs} 등이 식별되었습니다.\n\n"
        "자산배분 관점에서 단기적으로는 이벤트 리스크에 따른 변동성 확대에 대비하되, "
        "중기적 자산군 로테이션의 방향성은 거시 지표와 중앙은행 커뮤니케이션에 달려 있습니다. "
        "본 보고서는 투자 권유가 아닌 시장 분석 및 전망 참고자료입니다."
    )
    if scenarios:
        base += (
            f"\n\n기준 시나리오로는 「{scenarios[0].name}」을 설정하고 있으며, "
            f"발생 확률은 {scenarios[0].probability} 수준으로 평가합니다."
        )
    return base


def _build_regional_analysis(
    region: Region,
    regional_issues: list[ImpactAnalysis],
    all_issues: list[ImpactAnalysis],
) -> str:
    name = region_label(region)
    market_refs = {
        Region.US: "S&P 500, NASDAQ 및 미국 국채(Treasury)",
        Region.KR: "KOSPI, KOSDAQ 및 한국 국채",
        Region.JP: "닛케이 225(Nikkei 225), TOPIX 및 일본 국채(JGB)",
        Region.GLOBAL: "글로벌 자산시장",
    }
    markets = market_refs.get(region, "해당 시장")

    if not regional_issues:
        relevant = [i for i in all_issues if region in i.regions_affected][:3]
        regional_issues = relevant

    if not regional_issues:
        return (
            f"{name} 시장은 금일 보고서 분석 기간 내 직접적인 고영향 이슈가 제한적이었습니다. "
            f"다만 글로벌 리스크 심리와 환율·금리 연동 효과를 통해 {markets}에 "
            f"간접적 영향이 전이될 수 있으므로 지속적인 모니터링이 필요합니다."
        )

    paragraphs = [
        f"{name} 시장은 금일 {len(regional_issues)}건의 핵심 이슈가 부각되었습니다. "
        f"관련 자산군으로는 {markets} 등이 해당됩니다."
    ]

    for issue in regional_issues[:4]:
        sectors = ""
        if issue.affected_sectors:
            sectors = f" 영향이 예상되는 섹터는 {', '.join(issue.affected_sectors)}입니다."
        companies = ""
        if issue.affected_companies:
            companies = f" 개별 종목으로는 {', '.join(issue.affected_companies[:3])} 등이 주목됩니다."

        paragraphs.append(
            f"{_clean_title(issue.title_ko)}에 따르면, {_clean_summary(issue.summary_ko)} "
            f"주식 측면에서는 {issue.stock_impact}. 채권 시장에서는 {issue.bond_impact}. "
            f"금리 전망 측면에서는 {issue.rate_outlook}.{sectors}{companies}"
        )

    paragraphs.append(
        f"종합적으로 {name} 시장은 단기 이벤트에 민감하게 반응할 가능성이 있으며, "
        f"외부 변수의 전이 경로를 면밀히 추적할 필요가 있습니다."
    )
    return "\n\n".join(paragraphs)


def _build_asset_outlook(
    asset_name: str,
    issues: list[ImpactAnalysis],
    field: str,
) -> str:
    if not issues:
        return f"{asset_name} 시장에 대한 당일 유의미한 변화 요인이 제한적입니다."

    impacts = [getattr(i, field) for i in issues[:6]]
    unique = list(dict.fromkeys(impacts))

    body = (
        f"글로벌 {asset_name} 시장은 금일 복수의 매크로 변수가 교차하는 가운데 방향성 탐색 국면을 보이고 있습니다. "
        f"핵심 이슈들이 시사하는 방향성을 종합하면 다음과 같습니다."
    )
    for i, impact in enumerate(unique[:4], 1):
        body += f"\n\n우선, {_clean_title(issues[i-1].title_ko)}와 관련하여 {impact}."
    body += (
        f"\n\n이상의 요인들이 복합적으로 작용함에 따라, {asset_name} 시장은 "
        f"단기적으로 방향성 확정보다는 변동성 관리가 우선되는 국면으로 판단됩니다."
    )
    return body


def _build_fx_outlook(issues: list[ImpactAnalysis]) -> str:
    fx_issues = [i for i in issues if any("환율" in category_label(c) or c.value == "fx" for c in i.categories)]
    if not fx_issues:
        fx_issues = issues[:3]

    parts = [
        "환율 시장은 미국 달러(USD), 한국 원화(KRW), 일본 엔화(JPY) 간 상대적 강도 변화가 "
        "각국 주식·채권 시장 수급에 직접적인 영향을 미치고 있습니다."
    ]
    for issue in fx_issues[:4]:
        parts.append(
            f"{_clean_title(issue.title_ko)}의 맥락에서, {_clean_summary(issue.summary_ko)} "
            f"이는 수출주 환차익, 외국인 자금 흐름, 수입 물가 경로를 통해 시장에 반영될 수 있습니다."
        )
    parts.append(
        "환율 변동성 확대 국면에서는 헤지 비용과 포트폴리오 통화 노출도를 "
        "정기적으로 점검하는 것이 바람직합니다."
    )
    return "\n\n".join(parts)


def _build_thematic_analysis(issues: list[ImpactAnalysis]) -> str:
    by_category: dict[str, list[ImpactAnalysis]] = defaultdict(list)
    for issue in issues:
        for cat in issue.categories:
            by_category[category_label(cat)].append(issue)

    if not by_category:
        return "금일 특정 테마를 지배하는 단일 이슈보다는 복수 변수의 동시 작용이 관찰됩니다."

    intro = (
        "주제별로 이슈를 재구성하면, 시장은 개별 뉴스가 아닌 테마 단위로 가격을 형성하는 경향이 있습니다. "
        "금일 식별된 주요 테마는 다음과 같습니다."
    )
    theme_paragraphs = [intro]

    for theme, theme_issues in list(by_category.items())[:5]:
        titles = ", ".join(f"「{_clean_title(i.title_ko)}」" for i in theme_issues[:3])
        theme_paragraphs.append(
            f"**{theme}** 영역에서는 {titles} 등이 핵심 모니터링 포인트입니다. "
            f"{_clean_summary(theme_issues[0].summary_ko)} "
            f"이 테마는 단기 트레이딩뿐 아니라 중기 자산배분 관점에서도 중요한 함의를 갖습니다."
        )

    theme_paragraphs.append(
        "테마 간 상관관계 역시 주목할 필요가 있습니다. 예를 들어 금리·환율·원자재 변수는 "
        "동일한 거시 충격에 대해 서로 다른 시차로 반응할 수 있으며, "
        "이는 크로스에셋 전략 수립 시 반드시 고려해야 할 요소입니다."
    )
    return "\n\n".join(theme_paragraphs)


def _build_scenario_narrative(scenarios: list[Scenario]) -> str:
    if not scenarios:
        return "시나리오 분석을 위한 충분한 데이터가 확보되지 않았습니다."

    parts = [
        "전향적 시나리오 분석(Forward-looking Scenario Analysis)을 통해 "
        "향후 1~3개월 시장 경로를 점검합니다. "
        "각 시나리오는 발생 확률과 촉발 요인, 자산시장 함의를 포함합니다."
    ]

    for s in scenarios:
        triggers = ", ".join(s.triggers) if s.triggers else "별도 촉발 요인 미정"
        risks = ", ".join(s.key_risks) if s.key_risks else "없음"
        parts.append(
            f"**{s.name}** (추정 확률: {s.probability})\n\n"
            f"{s.description} 촉발 요인으로는 {triggers} 등이 제시됩니다.\n\n"
            f"미국 시장은 {s.us_market_outlook} 한국 시장은 {s.kr_market_outlook} "
            f"일본 시장은 {s.jp_market_outlook} 금리 전망은 {s.rate_outlook} "
            f"주요 리스크로는 {risks}이(가) 작용할 수 있습니다. "
            f"투자 시사점: {s.investment_implications}"
        )

    return "\n\n".join(parts)


def _build_risk_assessment(
    issues: list[ImpactAnalysis],
    scenarios: list[Scenario],
) -> str:
    high = [i for i in issues if i.impact_level == ImpactLevel.HIGH]
    high_titles = ", ".join(f"「{_clean_title(i.title_ko)}」" for i in high[:5])

    all_risks: list[str] = []
    for s in scenarios:
        all_risks.extend(s.key_risks)
    unique_risks = list(dict.fromkeys(all_risks))

    body = (
        f"리스크 모니터링 관점에서 금일 영향도가 높은 이슈는 {high_titles} 등입니다. "
        f"이들은 단기 변동성의 직접적 촉매가 될 수 있으며, "
        f"포지션 크기와 손실 한도 관리의 중요성을 시사합니다.\n\n"
        "시나리오 분석에서 도출된 주요 리스크 요인은 "
        f"{', '.join(unique_risks) if unique_risks else '지정학, 금리, 환율 변수'}입니다. "
        "이들 리스크가 동시에 현실화될 경우, 자산 간 상관관계가 급변하는 "
        "비정상적 시장 국면(tail risk)으로 전개될 수 있습니다.\n\n"
        "투자자는 이벤트 캘린더(중앙은행 회의, 주요 경제지표 발표, 지정학 일정)를 "
        "사전에 점검하고, 유동성 확보와 분산 투자 원칙을 유지하는 것이 바람직합니다."
    )
    return body


def _build_investment_strategy(scenarios: list[Scenario]) -> str:
    if not scenarios:
        return (
            "투자 전략 수립을 위해서는 추가 데이터 확보 및 심층 분석이 필요합니다. "
            "현 단계에서는 방어적 포지셔닝과 유동성 관리를 우선하는 것이 합리적입니다."
        )

    implications = [s.investment_implications for s in scenarios]
    base = (
        "투자 전략 및 포지셔닝 관점에서, 본 보고서는 특정 자산의 매수·매도를 권유하지 않습니다. "
        "다만 시나리오별 시사점을 종합하면 다음과 같은 운용 원칙을 도출할 수 있습니다.\n\n"
    )
    for i, (s, impl) in enumerate(zip(scenarios, implications), 1):
        base += f"{i}. {s.name} 시나리오 하에서는 {impl}\n"
    base += (
        "\n자산배분 측면에서 지역·섹터·듀레이션 분산을 유지하고, "
        "단기 이벤트 리스크에 대비한 헤지 수단(현금, 금, 옵션 등)의 역할을 재평가할 시점입니다."
    )
    return base


def _build_conclusion(report_date: str, issues: list[ImpactAnalysis]) -> str:
    return (
        f"결론적으로, {report_date} 기준 글로벌 매크로 환경은 불확실성이 잔존하는 가운데 "
        f"선별적 기회와 리스크가 공존하는 국면입니다. "
        f"본 보고서는 {len(issues)}건의 핵심 이슈를 바탕으로 미국·한국·일본 시장의 "
        f"단기 방향성과 중기 시나리오를 점검하였습니다. "
        f"투자 의사결정 시에는 본 분석을 보조 참고자료로 활용하되, "
        f"개별 투자자의 위험 성향과 투자 기간에 맞는 별도 검증이 반드시 필요합니다."
    )


def _clean_title(title: str) -> str:
    """[카테고리] 접두사 제거."""
    if title.startswith("[") and "]" in title:
        return title.split("]", 1)[1].strip()
    return title


def _clean_summary(summary: str) -> str:
    """자동 분류 접두사 및 원문 반복 제거."""
    text = summary.replace("[자동 분류] ", "")
    if "원문:" in text:
        text = text.split("원문:")[0].strip().rstrip(".")
    if text and not text.endswith("."):
        text += "."
    return text
