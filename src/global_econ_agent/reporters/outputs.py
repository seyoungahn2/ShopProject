from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReportOutputs:
    """생성된 보고서 파일 경로 모음."""
    markdown: Path | None = None
    csv: Path | None = None
    xlsx: Path | None = None
    google_sheets_url: str | None = None
    desktop_paths: list[Path] = field(default_factory=list)

    @property
    def all_paths(self) -> list[Path]:
        return [p for p in (self.markdown, self.csv, self.xlsx) if p is not None]

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        if self.markdown:
            lines.append(f"📄 Markdown: {self.markdown}")
        if self.csv:
            lines.append(f"📊 CSV: {self.csv}")
        if self.xlsx:
            lines.append(f"📗 Excel: {self.xlsx}")
        if self.desktop_paths:
            desktop_dir = self.desktop_paths[0].parent
            lines.append(f"🖥️ 바탕화면 복사본: {desktop_dir}")
            workspace_copy = next(
                (p.parent for p in self.desktop_paths if "workspace" in str(p.parent)),
                None,
            )
            if workspace_copy:
                lines.append(f"📁 프로젝트 복사본: {workspace_copy}")
        if self.google_sheets_url:
            lines.append(f"☁️ Google Sheets: {self.google_sheets_url}")
        return lines
