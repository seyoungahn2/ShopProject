import logging
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from global_econ_agent.analyzers.impact_analyzer import ImpactAnalyzer, ScenarioGenerator
from global_econ_agent.analyzers.research_composer import ResearchReportComposer
from global_econ_agent.collectors import collect_all
from global_econ_agent.config import Settings, get_settings
from global_econ_agent.models.schemas import Article, DailyReport, ResearchReportSections
from global_econ_agent.processors.classifier import ArticleClassifier, ArticleDeduplicator
from global_econ_agent.reporters.google_sheets_exporter import GoogleSheetsExporter
from global_econ_agent.reporters.outputs import ReportOutputs
from global_econ_agent.reporters.report_builder import ReportBuilder
from global_econ_agent.storage.database import Database

logger = logging.getLogger(__name__)


class GlobalEconAgent:
    """글로벌 경제 인텔리전스 에이전트 오케스트레이터."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()
        self.db = Database(self.settings)
        self.classifier = ArticleClassifier(self.settings.settings_yaml)
        self.deduplicator = ArticleDeduplicator()
        self.impact_analyzer = ImpactAnalyzer(self.settings)
        self.scenario_generator = ScenarioGenerator(self.settings)
        self.research_composer = ResearchReportComposer(self.settings)
        self.report_builder = ReportBuilder(
            self.settings.reports_dir,
            formats=self._resolve_report_formats(),
        )
        self.google_exporter = GoogleSheetsExporter(self.settings)
        self._load_analysis_config()

    def _resolve_report_formats(self) -> list[str]:
        formats = self.settings.get_report_formats()
        if self.settings.settings_yaml.exists():
            with open(self.settings.settings_yaml, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            yaml_formats = config.get("report", {}).get("formats")
            if yaml_formats:
                formats = yaml_formats
        return formats

    def _load_analysis_config(self) -> None:
        self.max_articles = 80
        self.top_issues_count = 15
        self.scenario_count = 3

        if self.settings.settings_yaml.exists():
            with open(self.settings.settings_yaml, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            analysis = config.get("analysis", {})
            self.max_articles = analysis.get("max_articles_per_run", 80)
            self.top_issues_count = analysis.get("top_issues_count", 15)
            self.scenario_count = analysis.get("scenario_count", 3)

    def run_daily_pipeline(self, report_date: str | None = None) -> tuple[DailyReport, ReportOutputs]:
        """일일 수집 → 분류 → 분석 → 보고서 생성 파이프라인."""
        report_date = report_date or datetime.now().strftime("%Y-%m-%d")
        logger.info("=== 일일 파이프라인 시작: %s ===", report_date)

        logger.info("[1/5] 뉴스 수집 중...")
        articles = collect_all(self.settings)
        articles_collected = len(articles)

        logger.info("[2/5] 분류 및 중복 제거 중...")
        articles = self.classifier.classify_batch(articles)
        articles = self.deduplicator.deduplicate(articles)
        articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)
        articles = articles[: self.max_articles]

        logger.info("[3/5] DB 저장 중...")
        self.db.save_articles(articles)

        logger.info("[4/5] AI 영향 분석 중...")
        key_issues = self.impact_analyzer.analyze_articles(articles, self.top_issues_count)

        for issue in key_issues:
            for article in articles:
                if article.id == issue.article_id or article.title == issue.title_original:
                    article.is_key_issue = True
                    self.db.update_article(article)
                    break

        logger.info("[5/6] 시나리오 분석 중...")
        executive_summary, scenarios, term_glossary = self.scenario_generator.generate(
            key_issues, self.scenario_count
        )

        logger.info("[6/6] 전문 리서치 보고서 작성 중...")
        research = self.research_composer.compose(
            report_date=report_date,
            executive_summary=executive_summary,
            key_issues=key_issues,
            scenarios=scenarios,
            articles_collected=articles_collected,
        )

        report = DailyReport(
            report_date=report_date,
            executive_summary=executive_summary,
            key_issues=key_issues,
            scenarios=scenarios,
            term_glossary=term_glossary,
            research=research,
            articles_collected=articles_collected,
            articles_analyzed=len(key_issues),
        )

        outputs = self._export_report(report)
        logger.info("=== 파이프라인 완료 ===")
        return report, outputs

    def _export_report(self, report: DailyReport) -> ReportOutputs:
        outputs = self.report_builder.build(report)

        if self.google_exporter.is_configured():
            outputs.google_sheets_url = self.google_exporter.export(report)

        outputs = self._copy_to_accessible_locations(outputs)

        primary_path = (
            outputs.markdown
            or outputs.xlsx
            or outputs.csv
            or Path("")
        )
        self.db.save_report(report, str(primary_path))

        return outputs

    def _copy_to_accessible_locations(self, outputs: ReportOutputs) -> ReportOutputs:
        """보고서를 바탕화면·프로젝트 루트 등 쉬운 위치에 복사."""
        copy_targets = [
            Path.home() / "Desktop" / "글로벌경제보고서",
            self.settings.project_root / "글로벌경제보고서",
        ]

        copied: list[Path] = []
        for target_dir in copy_targets:
            target_dir.mkdir(parents=True, exist_ok=True)
            for src in outputs.all_paths:
                dest = target_dir / src.name
                if src.resolve() == dest.resolve():
                    copied.append(dest)
                    continue
                shutil.copy2(src, dest)
                copied.append(dest)
            self._write_location_readme(target_dir)

        if copied:
            logger.info("보고서 복사 완료: %s", copy_targets[0])

        outputs.desktop_paths = copied
        return outputs

    def _write_location_readme(self, folder: Path) -> None:
        readme = folder / "여기에_보고서가_있습니다.txt"
        readme.write_text(
            "글로벌 경제 리서치 보고서 저장 폴더\n\n"
            f"폴더 경로: {folder.resolve()}\n\n"
            "파일 설명:\n"
            "- report_YYYY-MM-DD.md   → 읽기용 보고서 (Markdown)\n"
            "- report_YYYY-MM-DD.xlsx → 엑셀/구글 시트용\n"
            "- report_YYYY-MM-DD.csv  → CSV\n\n"
            "새 보고서 생성: global-econ run\n",
            encoding="utf-8",
        )

    def collect_only(self) -> list[Article]:
        articles = collect_all(self.settings)
        articles = self.classifier.classify_batch(articles)
        articles = self.deduplicator.deduplicate(articles)
        self.db.save_articles(articles)
        return articles

    def analyze_existing(self, report_date: str | None = None) -> tuple[DailyReport, ReportOutputs]:
        report_date = report_date or datetime.now().strftime("%Y-%m-%d")
        articles = self.db.get_recent_articles(hours=48, limit=self.max_articles)

        if not articles:
            logger.warning("분석할 기사가 없습니다. 먼저 collect를 실행하세요.")
            report = DailyReport(
                report_date=report_date,
                executive_summary="수집된 기사가 없습니다.",
                research=ResearchReportSections(
                    investment_summary="수집된 기사가 없어 리서치 보고서를 작성할 수 없습니다.",
                    conclusion="먼저 `global-econ collect` 또는 `global-econ run`을 실행하세요.",
                ),
            )
            outputs = self._export_report(report)
            return report, outputs

        key_issues = self.impact_analyzer.analyze_articles(articles, self.top_issues_count)
        executive_summary, scenarios, term_glossary = self.scenario_generator.generate(
            key_issues, self.scenario_count
        )

        research = self.research_composer.compose(
            report_date=report_date,
            executive_summary=executive_summary,
            key_issues=key_issues,
            scenarios=scenarios,
            articles_collected=len(articles),
        )

        report = DailyReport(
            report_date=report_date,
            executive_summary=executive_summary,
            key_issues=key_issues,
            scenarios=scenarios,
            term_glossary=term_glossary,
            research=research,
            articles_collected=len(articles),
            articles_analyzed=len(key_issues),
        )

        outputs = self._export_report(report)
        return report, outputs
