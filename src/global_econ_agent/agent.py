import logging
from datetime import datetime
from pathlib import Path

import yaml

from global_econ_agent.analyzers.impact_analyzer import ImpactAnalyzer, ScenarioGenerator
from global_econ_agent.collectors import collect_all
from global_econ_agent.config import Settings, get_settings
from global_econ_agent.models.schemas import Article, DailyReport
from global_econ_agent.processors.classifier import ArticleClassifier, ArticleDeduplicator
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
        self.report_builder = ReportBuilder(self.settings.reports_dir)
        self._load_analysis_config()

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

    def run_daily_pipeline(self, report_date: str | None = None) -> DailyReport:
        """일일 수집 → 분류 → 분석 → 보고서 생성 파이프라인."""
        report_date = report_date or datetime.now().strftime("%Y-%m-%d")
        logger.info("=== 일일 파이프라인 시작: %s ===", report_date)

        # 1. 수집
        logger.info("[1/5] 뉴스 수집 중...")
        articles = collect_all(self.settings)
        articles_collected = len(articles)

        # 2. 분류 및 중복 제거
        logger.info("[2/5] 분류 및 중복 제거 중...")
        articles = self.classifier.classify_batch(articles)
        articles = self.deduplicator.deduplicate(articles)
        articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)
        articles = articles[: self.max_articles]

        # 3. 저장
        logger.info("[3/5] DB 저장 중...")
        self.db.save_articles(articles)

        # 4. AI 영향 분석
        logger.info("[4/5] AI 영향 분석 중...")
        key_issues = self.impact_analyzer.analyze_articles(articles, self.top_issues_count)

        for issue in key_issues:
            for article in articles:
                if article.id == issue.article_id or article.title == issue.title:
                    article.is_key_issue = True
                    self.db.update_article(article)
                    break

        # 5. 시나리오 생성
        logger.info("[5/5] 시나리오 보고서 생성 중...")
        executive_summary, scenarios = self.scenario_generator.generate(
            key_issues, self.scenario_count
        )

        report = DailyReport(
            report_date=report_date,
            executive_summary=executive_summary,
            key_issues=key_issues,
            scenarios=scenarios,
            articles_collected=articles_collected,
            articles_analyzed=len(key_issues),
        )

        output_path = self.report_builder.build(report)
        self.db.save_report(report, str(output_path))

        logger.info("=== 파이프라인 완료: %s ===", output_path)
        return report

    def collect_only(self) -> list[Article]:
        """수집만 실행."""
        articles = collect_all(self.settings)
        articles = self.classifier.classify_batch(articles)
        articles = self.deduplicator.deduplicate(articles)
        self.db.save_articles(articles)
        return articles

    def analyze_existing(self, report_date: str | None = None) -> DailyReport:
        """DB에 저장된 기사를 기반으로 분석만 실행."""
        report_date = report_date or datetime.now().strftime("%Y-%m-%d")
        articles = self.db.get_recent_articles(hours=48, limit=self.max_articles)

        if not articles:
            logger.warning("분석할 기사가 없습니다. 먼저 collect를 실행하세요.")
            return DailyReport(
                report_date=report_date,
                executive_summary="수집된 기사가 없습니다.",
            )

        key_issues = self.impact_analyzer.analyze_articles(articles, self.top_issues_count)
        executive_summary, scenarios = self.scenario_generator.generate(
            key_issues, self.scenario_count
        )

        report = DailyReport(
            report_date=report_date,
            executive_summary=executive_summary,
            key_issues=key_issues,
            scenarios=scenarios,
            articles_collected=len(articles),
            articles_analyzed=len(key_issues),
        )

        output_path = self.report_builder.build(report)
        self.db.save_report(report, str(output_path))
        return report
