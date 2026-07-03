from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReportOutputs:
    """생성된 보고서 파일 경로 모음."""
    markdown: Path | None = None
    csv: Path | None = None
    xlsx: Path | None = None
    google_sheets_url: str | None = None

    @property
    def all_paths(self) -> list[Path]:
        return [p for p in (self.markdown, self.csv, self.xlsx) if p is not None]

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        if self.markdown:
            lines.append(f"📄 Markdown: {self.markdown}")
        if self.csv:
            lines.append(f"📊 CSV (구글 시트 업로드 가능): {self.csv}")
        if self.xlsx:
            lines.append(f"📗 Excel: {self.xlsx}")
        if self.google_sheets_url:
            lines.append(f"☁️ Google Sheets: {self.google_sheets_url}")
        return lines
