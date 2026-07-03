import logging

from global_econ_agent.config import Settings
from global_econ_agent.models.schemas import DailyReport
from global_econ_agent.utils.labels import category_label, impact_label, region_label

logger = logging.getLogger(__name__)


class GoogleSheetsExporter:
    """Google Sheets에 보고서를 직접 업로드합니다 (선택 기능).

    사전 준비:
    1. Google Cloud에서 서비스 계정 생성
    2. Google Sheets API 활성화
    3. 서비스 계정 JSON 키 파일 다운로드
    4. 대상 스프레드시트에 서비스 계정 이메일을 편집자로 공유
  """

    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.google_sheets_enabled
            and self.settings.google_service_account_json
            and self.settings.google_spreadsheet_id
        )

    def export(self, report: DailyReport) -> str | None:
        if not self.is_configured():
            logger.info("Google Sheets 미설정 — 건너뜀")
            return None

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            logger.warning(
                "gspread 미설치 — pip install 'global-econ-agent[google]' 로 설치하세요"
            )
            return None

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            str(self.settings.google_service_account_json),
            scopes=scopes,
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(self.settings.google_spreadsheet_id)

        sheet_name = f"{report.report_date}"
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=15)

        rows: list[list[str]] = [
            ["글로벌 경제 시나리오 보고서", report.report_date],
            ["경영진 요약", report.executive_summary],
            [],
            [
                "번호", "한글 제목", "원문 제목", "영향도", "카테고리", "영향 지역",
                "주식 영향", "채권 영향", "금리 전망", "요약", "용어 해석",
            ],
        ]

        for i, issue in enumerate(report.key_issues, 1):
            glossary_text = "\n".join(
                f"{g.term}: {g.meaning_ko}" for g in issue.term_glossary
            )
            rows.append([
                str(i),
                issue.title_ko,
                issue.title_original,
                impact_label(issue.impact_level),
                ", ".join(category_label(c) for c in issue.categories),
                ", ".join(region_label(r) for r in issue.regions_affected),
                issue.stock_impact,
                issue.bond_impact,
                issue.rate_outlook,
                issue.summary_ko,
                glossary_text,
            ])

        rows.extend([[], ["시나리오 전망"]])
        rows.append([
            "시나리오", "확률", "설명", "미국", "한국", "일본", "금리", "투자 시사점",
        ])
        for scenario in report.scenarios:
            rows.append([
                scenario.name,
                scenario.probability,
                scenario.description,
                scenario.us_market_outlook,
                scenario.kr_market_outlook,
                scenario.jp_market_outlook,
                scenario.rate_outlook,
                scenario.investment_implications,
            ])

        if report.term_glossary:
            rows.extend([[], ["전체 용어 해석집"], ["원어", "한글 해석"]])
            for g in report.term_glossary:
                rows.append([g.term, g.meaning_ko])

        worksheet.update(rows, value_input_option="USER_ENTERED")

        url = f"https://docs.google.com/spreadsheets/d/{self.settings.google_spreadsheet_id}/edit#gid={worksheet.id}"
        logger.info("Google Sheets 업로드 완료: %s", url)
        return url
