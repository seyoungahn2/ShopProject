import pytest

from global_econ_agent.analyzers.research_composer import ResearchReportComposer
from global_econ_agent.config import Settings
from global_econ_agent.models.schemas import (
    DailyReport,
    ImpactAnalysis,
    ImpactLevel,
    Region,
    ResearchReportSections,
    Scenario,
    TermGlossary,
)
from global_econ_agent.reporters.report_builder import ReportBuilder
from global_econ_agent.utils.glossary import extract_glossary, merge_glossaries


def test_extract_glossary_fed():
    glossary = extract_glossary("Fed raised rates at FOMC meeting")
    terms = {g.term for g in glossary}
    assert "Fed" in terms
    assert "FOMC" in terms
    assert all(g.meaning_ko for g in glossary)


def test_merge_glossaries_dedup():
    a = [TermGlossary(term="Fed", meaning_ko="연준")]
    b = [TermGlossary(term="Fed", meaning_ko="미국 중앙은행"), TermGlossary(term="BOJ", meaning_ko="일본은행")]
    merged = merge_glossaries(a, b)
    assert len(merged) == 2
    fed = next(g for g in merged if g.term == "Fed")
    assert fed.meaning_ko == "연준"


def test_research_composer_fallback():
    composer = ResearchReportComposer(Settings(openai_api_key=""))
    issues = [
        ImpactAnalysis(
            article_id="1",
            title_ko="연준(Fed) 금리 동결",
            title_original="Fed holds rates",
            categories=[],
            regions_affected=[Region.US],
            impact_level=ImpactLevel.HIGH,
            stock_impact="금융주 강세",
            bond_impact="국채 보합",
            rate_outlook="동결 기조",
            summary_ko="연준이 기준금리를 동결했습니다.",
        )
    ]
    scenarios = [
        Scenario(
            name="기준 시나리오",
            probability="50%",
            description="현 추세 유지",
            us_market_outlook="박스권",
            kr_market_outlook="보합",
            jp_market_outlook="보합",
            rate_outlook="동결",
            investment_implications="분산 투자",
        )
    ]
    research = composer.compose("2026-07-03", "요약", issues, scenarios, 100)

    assert research.investment_summary
    assert len(research.key_takeaways) >= 1
    assert "미국" in research.us_analysis or "Fed" in research.us_analysis
    assert research.conclusion


def test_report_builder_research_format(tmp_path):
    research = ResearchReportSections(
        report_title="글로벌 매크로 & 멀티에셋 투자 리서치",
        subtitle="Daily Strategy Note",
        investment_summary="투자 요약 본문입니다.",
        key_takeaways=["핵심 시사점 1", "핵심 시사점 2"],
        macro_overview="거시경제 분석 본문입니다.",
        us_analysis="미국 시장 분석입니다.",
        kr_analysis="한국 시장 분석입니다.",
        jp_analysis="일본 시장 분석입니다.",
        equity_outlook="주식 전망입니다.",
        bond_outlook="채권 전망입니다.",
        fx_outlook="환율 전망입니다.",
        rate_outlook_section="금리 전망입니다.",
        thematic_analysis="테마 분석입니다.",
        scenario_analysis="시나리오 분석입니다.",
        risk_assessment="리스크 분석입니다.",
        investment_strategy="투자 전략입니다.",
        conclusion="결론입니다.",
    )

    report = DailyReport(
        report_date="2026-07-03",
        executive_summary="요약",
        research=research,
        key_issues=[
            ImpactAnalysis(
                article_id="1",
                title_ko="연준(Fed) 금리 동결",
                title_original="Fed holds rates steady",
                categories=[],
                regions_affected=[Region.US],
                impact_level=ImpactLevel.HIGH,
                stock_impact="금융주 강세",
                bond_impact="국채 보합",
                rate_outlook="동결 기조",
                summary_ko="연준이 기준금리를 동결했습니다.",
                term_glossary=[TermGlossary(term="Fed", meaning_ko="연방준비제도 — 미국 중앙은행")],
            )
        ],
        term_glossary=[TermGlossary(term="Fed", meaning_ko="연방준비제도 — 미국 중앙은행")],
        articles_collected=10,
        articles_analyzed=1,
    )

    builder = ReportBuilder(tmp_path, formats=["markdown", "xlsx", "csv"])
    outputs = builder.build(report)

    assert outputs.markdown and outputs.markdown.exists()
    md = outputs.markdown.read_text(encoding="utf-8")
    assert "투자 요약 (Investment Summary)" in md
    assert "거시경제 환경 분석 (Macro Overview)" in md
    assert "시나리오 분석 (Scenario Analysis)" in md
    assert "투자 요약 본문입니다." in md
    assert "부록 A. 전문 용어 해석" in md
    assert "| 항목 | 내용 |" not in md  # 표 형식 제거
