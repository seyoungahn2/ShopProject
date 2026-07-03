from pathlib import Path

from jinja2 import Environment

from global_econ_agent.models.schemas import DailyReport
from global_econ_agent.reporters.outputs import ReportOutputs
from global_econ_agent.reporters.spreadsheet_exporter import SpreadsheetExporter
from global_econ_agent.utils.glossary import format_glossary_inline

RESEARCH_REPORT_TEMPLATE = """# {{ research.report_title }}

## {{ research.subtitle }} | {{ report_date_ko }}

---

**발행일:** {{ report.report_date }}  
**발행 시각:** {{ report.generated_at.strftime('%Y-%m-%d %H:%M') }} (UTC)  
**커버리지:** 미국 · 한국 · 일본 | 주식 · 채권 · 환율 · 금리  
**분석 기반:** 공개 뉴스 {{ report.articles_collected }}건 수집, 핵심 이슈 {{ report.articles_analyzed }}건 분석  
**문서 분류:** 자동 생성 리서치 참고자료 (투자 권유 아님)

---

## I. 투자 요약 (Investment Summary)

{{ research.investment_summary }}

## II. 핵심 시사점 (Key Takeaways)

{% for item in research.key_takeaways %}
{{ loop.index }}. {{ item }}
{% endfor %}

## III. 거시경제 환경 분석 (Macro Overview)

{{ research.macro_overview }}

## IV. 지역별 시장 전망 (Regional Outlook)

### 4.1 미국 (United States)

{{ research.us_analysis }}

### 4.2 한국 (Korea)

{{ research.kr_analysis }}

### 4.3 일본 (Japan)

{{ research.jp_analysis }}

## V. 자산군별 전망 (Asset Class Outlook)

### 5.1 주식시장 (Equities)

{{ research.equity_outlook }}

### 5.2 채권시장 (Fixed Income)

{{ research.bond_outlook }}

### 5.3 환율 (Foreign Exchange)

{{ research.fx_outlook }}

### 5.4 금리 (Interest Rates)

{{ research.rate_outlook_section }}

## VI. 주제별 심층 분석 (Thematic Deep Dive)

{{ research.thematic_analysis }}

## VII. 시나리오 분석 (Scenario Analysis)

{{ research.scenario_analysis }}

## VIII. 리스크 요인 (Risk Monitor)

{{ research.risk_assessment }}

## IX. 투자 전략 및 포지셔닝 (Investment Strategy)

{{ research.investment_strategy }}

## X. 결론 (Conclusion)

{{ research.conclusion }}

---

## 부록 A. 전문 용어 해석 (Glossary)

본 보고서에서 사용된 원어 전문 용어에 대한 한글 해석입니다.

{% if report.term_glossary %}
{{ format_glossary(report.term_glossary) }}
{% else %}
해당 없음
{% endif %}

## 부록 B. 참고 이슈 목록 (Reference Issues)

{% for issue in report.key_issues %}
**{{ loop.index }}. {{ issue.title_ko }}**{% if issue.title_original and issue.title_original != issue.title_ko %} *(원문: {{ issue.title_original }})*{% endif %}

{{ issue.summary_ko }}

{% endfor %}

## 부록 C. 면책 조항 (Disclaimer)

본 보고서는 Global Econ Intelligence Agent가 공개적으로 이용 가능한 뉴스·정보를
자동 수집·분석하여 작성한 참고 자료이며, 특정 금융상품의 매수·매도 또는 투자 권유가 아닙니다.
본 문서에 수록된 전망, 시나리오, 의견은 작성 시점의 정보에 기반하며, 사후 변경될 수 있습니다.
투자 결정과 그에 따른 손익은 전적으로 투자자 본인에게 귀속됩니다.
금융투자상품은 원금 손실 가능성이 있으며, 투자 전 반드시 전문가와 상담하시기 바랍니다.

---

*Global Econ Intelligence Agent — Automated Macro Research*
"""


class ReportBuilder:
    def __init__(self, reports_dir: Path, formats: list[str] | None = None):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.formats = formats or ["markdown", "xlsx", "csv"]
        self.spreadsheet_exporter = SpreadsheetExporter(reports_dir)

    def build(self, report: DailyReport) -> ReportOutputs:
        outputs = ReportOutputs()
        base_name = f"report_{report.report_date}"

        if "markdown" in self.formats:
            outputs.markdown = self._build_markdown(report, base_name)

        if "xlsx" in self.formats:
            outputs.xlsx = self.spreadsheet_exporter.export_xlsx(report, base_name)

        if "csv" in self.formats:
            outputs.csv = self.spreadsheet_exporter.export_csv(report, base_name)

        return outputs

    def _build_markdown(self, report: DailyReport, base_name: str) -> Path:
        env = Environment()
        env.globals["format_glossary"] = format_glossary_inline

        template = env.from_string(RESEARCH_REPORT_TEMPLATE)
        report_date_ko = _format_date_ko(report.report_date)

        markdown = template.render(
            report=report,
            research=report.research,
            report_date_ko=report_date_ko,
        )

        output_path = self.reports_dir / f"{base_name}.md"
        output_path.write_text(markdown, encoding="utf-8")
        return output_path


def _format_date_ko(date_str: str) -> str:
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            y, m, d = parts
            return f"{y}년 {int(m)}월 {int(d)}일"
    except (ValueError, IndexError):
        pass
    return date_str
