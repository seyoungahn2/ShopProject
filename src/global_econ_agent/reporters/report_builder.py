from pathlib import Path

from jinja2 import Environment

from global_econ_agent.models.schemas import DailyReport, ImpactLevel
from global_econ_agent.reporters.outputs import ReportOutputs
from global_econ_agent.reporters.spreadsheet_exporter import SpreadsheetExporter
from global_econ_agent.utils.glossary import format_glossary_inline
from global_econ_agent.utils.labels import category_label, impact_label, region_label

REPORT_TEMPLATE = """# {{ title }}

> 생성일시: {{ report.generated_at.strftime('%Y-%m-%d %H:%M') }} (UTC)
> 수집 기사: {{ report.articles_collected }}건 | 분석 이슈: {{ report.articles_analyzed }}건

---

## 경영진 요약

{{ report.executive_summary }}

---

## 주요 핵심 이슈

{% for issue in report.key_issues %}
### {{ loop.index }}. {{ issue.title_ko }}

{% if issue.title_original and issue.title_original != issue.title_ko %}
> 원문 제목: {{ issue.title_original }}
{% endif %}

| 항목 | 내용 |
|------|------|
| **영향도** | {{ impact_emoji(issue.impact_level) }} {{ impact_label(issue.impact_level) }} |
| **카테고리** | {{ issue.categories | map('category_label') | join(', ') }} |
| **영향 지역** | {{ issue.regions_affected | map('region_label') | join(', ') }} |
| **주식 영향** | {{ issue.stock_impact }} |
| **채권 영향** | {{ issue.bond_impact }} |
| **금리 전망** | {{ issue.rate_outlook }} |

**요약:** {{ issue.summary_ko }}

{% if issue.affected_sectors %}
**영향 섹터:** {{ issue.affected_sectors | join(', ') }}
{% endif %}
{% if issue.affected_companies %}
**관련 기업:** {{ issue.affected_companies | join(', ') }}
{% endif %}

{% if issue.term_glossary %}
**용어 해석:**
{{ format_glossary(issue.term_glossary) }}
{% endif %}

---
{% endfor %}

## 시나리오 전망

{% for scenario in report.scenarios %}
### {{ scenario.name }} (발생 확률: {{ scenario.probability }})

{{ scenario.description }}

**촉발 요인:**
{% for trigger in scenario.triggers %}- {{ trigger }}
{% endfor %}

| 시장 | 전망 |
|------|------|
| 미국 | {{ scenario.us_market_outlook }} |
| 한국 | {{ scenario.kr_market_outlook }} |
| 일본 | {{ scenario.jp_market_outlook }} |
| 금리 | {{ scenario.rate_outlook }} |

**주요 리스크:**
{% for risk in scenario.key_risks %}- {{ risk }}
{% endfor %}

**투자 시사점:** {{ scenario.investment_implications }}

{% if scenario.term_glossary %}
**용어 해석:**
{{ format_glossary(scenario.term_glossary) }}
{% endif %}

---
{% endfor %}

{% if report.term_glossary %}
## 전체 용어 해석집

본 보고서에서 사용된 원어 전문 용어와 한글 해석입니다.

{{ format_glossary(report.term_glossary) }}

---
{% endif %}

## 면책 조항

본 보고서는 AI 에이전트가 공개 뉴스 소스를 기반으로 자동 생성한 참고 자료입니다.
투자 결정의 유일한 근거로 사용해서는 안 되며, 반드시 전문가 상담과 추가 검증이 필요합니다.

---
*Global Econ Intelligence Agent v0.1*
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
        env.filters["region_label"] = region_label
        env.filters["category_label"] = category_label
        env.globals["impact_emoji"] = _impact_emoji
        env.globals["impact_label"] = impact_label
        env.globals["format_glossary"] = format_glossary_inline

        template = env.from_string(REPORT_TEMPLATE)

        title = f"글로벌 경제 시나리오 보고서 — {report.report_date}"
        markdown = template.render(report=report, title=title)

        output_path = self.reports_dir / f"{base_name}.md"
        output_path.write_text(markdown, encoding="utf-8")
        return output_path


def _impact_emoji(level: ImpactLevel) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(level.value, "⚪")
