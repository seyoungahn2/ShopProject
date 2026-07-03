import pytest

from global_econ_agent.models.schemas import (
    DailyReport,
    ImpactAnalysis,
    ImpactLevel,
    Region,
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
    assert fed.meaning_ko == "연준"  # 먼저 들어온 값 유지


def test_report_builder_multi_format(tmp_path):
    report = DailyReport(
        report_date="2026-07-03",
        executive_summary="오늘 시장은 변동성이 확대되었습니다.",
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
    assert outputs.xlsx and outputs.xlsx.exists()
    assert outputs.csv and outputs.csv.exists()

    md_content = outputs.markdown.read_text(encoding="utf-8")
    assert "연준(Fed) 금리 동결" in md_content
    assert "용어 해석" in md_content
    assert "Fed" in md_content
