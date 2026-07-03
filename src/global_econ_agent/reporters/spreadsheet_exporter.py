import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from global_econ_agent.models.schemas import DailyReport, ResearchReportSections
from global_econ_agent.utils.labels import category_label, impact_label, region_label


class SpreadsheetExporter:
    """CSV·Excel 형식으로 리서치 보고서를 저장합니다."""

    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, report: DailyReport, base_name: str) -> Path:
        output_path = self.reports_dir / f"{base_name}.csv"
        r = report.research

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["글로벌 매크로 & 멀티에셋 투자 리서치", report.report_date])
            writer.writerow([])

            sections = [
                ("I. 투자 요약", r.investment_summary),
                ("II. 핵심 시사점", "\n".join(f"{i+1}. {t}" for i, t in enumerate(r.key_takeaways))),
                ("III. 거시경제 환경 분석", r.macro_overview),
                ("IV-1. 미국 시장", r.us_analysis),
                ("IV-2. 한국 시장", r.kr_analysis),
                ("IV-3. 일본 시장", r.jp_analysis),
                ("V-1. 주식시장", r.equity_outlook),
                ("V-2. 채권시장", r.bond_outlook),
                ("V-3. 환율", r.fx_outlook),
                ("V-4. 금리", r.rate_outlook_section),
                ("VI. 주제별 심층 분석", r.thematic_analysis),
                ("VII. 시나리오 분석", r.scenario_analysis),
                ("VIII. 리스크 요인", r.risk_assessment),
                ("IX. 투자 전략", r.investment_strategy),
                ("X. 결론", r.conclusion),
            ]
            for title, body in sections:
                writer.writerow([title, body])
                writer.writerow([])

            if report.term_glossary:
                writer.writerow(["부록. 용어 해석"])
                writer.writerow(["원어", "한글 해석"])
                for g in report.term_glossary:
                    writer.writerow([g.term, g.meaning_ko])

        return output_path

    def export_xlsx(self, report: DailyReport, base_name: str) -> Path:
        output_path = self.reports_dir / f"{base_name}.xlsx"
        wb = Workbook()

        self._write_research_sheet(wb.active, report)
        self._write_issues_sheet(wb.create_sheet("참고이슈"), report)
        self._write_scenarios_sheet(wb.create_sheet("시나리오"), report)
        if report.term_glossary:
            self._write_glossary_sheet(wb.create_sheet("용어해석"), report)

        wb.save(output_path)
        return output_path

    def _write_research_sheet(self, ws, report: DailyReport) -> None:
        ws.title = "리서치보고서"
        r = report.research
        header_font = Font(bold=True, size=11, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1A3A5C")
        title_font = Font(bold=True, size=14)

        ws.cell(row=1, column=1, value=r.report_title).font = title_font
        ws.cell(row=2, column=1, value=f"{r.subtitle} | {report.report_date}")
        ws.cell(row=3, column=1, value=f"분석 기반: 뉴스 {report.articles_collected}건, 이슈 {report.articles_analyzed}건")

        sections = [
            ("I. 투자 요약 (Investment Summary)", r.investment_summary),
            ("II. 핵심 시사점 (Key Takeaways)", "\n".join(f"{i+1}. {t}" for i, t in enumerate(r.key_takeaways))),
            ("III. 거시경제 환경 분석 (Macro Overview)", r.macro_overview),
            ("IV-1. 미국 (United States)", r.us_analysis),
            ("IV-2. 한국 (Korea)", r.kr_analysis),
            ("IV-3. 일본 (Japan)", r.jp_analysis),
            ("V-1. 주식시장 (Equities)", r.equity_outlook),
            ("V-2. 채권시장 (Fixed Income)", r.bond_outlook),
            ("V-3. 환율 (FX)", r.fx_outlook),
            ("V-4. 금리 (Interest Rates)", r.rate_outlook_section),
            ("VI. 주제별 심층 분석 (Thematic Deep Dive)", r.thematic_analysis),
            ("VII. 시나리오 분석 (Scenario Analysis)", r.scenario_analysis),
            ("VIII. 리스크 요인 (Risk Monitor)", r.risk_assessment),
            ("IX. 투자 전략 (Investment Strategy)", r.investment_strategy),
            ("X. 결론 (Conclusion)", r.conclusion),
        ]

        row = 5
        for title, body in sections:
            cell = ws.cell(row=row, column=1, value=title)
            cell.font = header_font
            cell.fill = header_fill
            ws.cell(row=row, column=2, value=body).alignment = Alignment(wrap_text=True, vertical="top")
            row += 2

        ws.column_dimensions["A"].width = 36
        ws.column_dimensions["B"].width = 100

    def _write_issues_sheet(self, ws, report: DailyReport) -> None:
        headers = [
            "번호", "한글 제목", "원문 제목", "영향도", "카테고리", "영향 지역", "요약",
        ]
        self._write_header_row(ws, headers)

        for i, issue in enumerate(report.key_issues, 1):
            row = [
                i,
                issue.title_ko,
                issue.title_original,
                impact_label(issue.impact_level),
                ", ".join(category_label(c) for c in issue.categories),
                ", ".join(region_label(r) for r in issue.regions_affected),
                issue.summary_ko,
            ]
            self._write_data_row(ws, i + 1, row)
        self._auto_width(ws)

    def _write_scenarios_sheet(self, ws, report: DailyReport) -> None:
        headers = ["시나리오", "확률", "설명", "미국", "한국", "일본", "금리", "투자 시사점"]
        self._write_header_row(ws, headers)

        for i, scenario in enumerate(report.scenarios, 1):
            row = [
                scenario.name,
                scenario.probability,
                scenario.description,
                scenario.us_market_outlook,
                scenario.kr_market_outlook,
                scenario.jp_market_outlook,
                scenario.rate_outlook,
                scenario.investment_implications,
            ]
            self._write_data_row(ws, i + 1, row)
        self._auto_width(ws)

    def _write_glossary_sheet(self, ws, report: DailyReport) -> None:
        self._write_header_row(ws, ["원어", "한글 해석"])
        for i, g in enumerate(report.term_glossary, 1):
            self._write_data_row(ws, i + 1, [g.term, g.meaning_ko])
        ws.column_dimensions["A"].width = 24
        ws.column_dimensions["B"].width = 60

    def _write_header_row(self, ws, headers: list[str]) -> None:
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1A73E8")
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

    def _write_data_row(self, ws, row: int, values: list) -> None:
        for col, value in enumerate(values, 1):
            ws.cell(row=row, column=col, value=value).alignment = Alignment(
                wrap_text=True, vertical="top"
            )

    def _auto_width(self, ws) -> None:
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_len = max(max_len, min(len(str(cell.value)), 50))
            ws.column_dimensions[col_letter].width = max(max_len + 2, 12)
