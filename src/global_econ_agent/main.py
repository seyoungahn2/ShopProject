import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from global_econ_agent import __version__
from global_econ_agent.agent import GlobalEconAgent
from global_econ_agent.config import get_settings
from global_econ_agent.scheduler.daily_job import start_scheduler

app = typer.Typer(
    name="global-econ",
    help="글로벌 경제 이슈 수집·분석·시나리오 보고서 AI 에이전트",
    add_completion=False,
)
console = Console()


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 로그 출력"),
) -> None:
    _setup_logging(verbose)


@app.command()
def run(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="보고서 날짜 (YYYY-MM-DD)"),
) -> None:
    """전체 파이프라인 실행: 수집 → 분석 → 보고서 생성."""
    console.print(Panel.fit(
        f"[bold blue]Global Econ Intelligence Agent[/bold blue] v{__version__}\n"
        "수집 → 분류 → AI 분석 → 시나리오 보고서 생성",
        border_style="blue",
    ))

    settings = get_settings()
    if not settings.openai_api_key:
        console.print("[yellow]⚠ OPENAI_API_KEY 미설정 — 규칙 기반 분석으로 동작합니다.[/yellow]")

    agent = GlobalEconAgent(settings)
    report = agent.run_daily_pipeline(date)

    _print_report_summary(report, settings.reports_dir)


@app.command()
def collect() -> None:
    """뉴스 수집만 실행."""
    console.print("[bold]뉴스 수집 시작...[/bold]")
    agent = GlobalEconAgent()
    articles = agent.collect_only()
    console.print(f"[green]✓ {len(articles)}건 수집 완료[/green]")

    table = Table(title="수집 결과 (상위 10건)")
    table.add_column("점수", style="cyan")
    table.add_column("지역")
    table.add_column("제목")
    for a in articles[:10]:
        table.add_row(
            str(a.relevance_score),
            a.region.value,
            a.title[:60] + ("..." if len(a.title) > 60 else ""),
        )
    console.print(table)


@app.command()
def analyze(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="보고서 날짜"),
) -> None:
    """저장된 기사 기반 분석 및 보고서 생성."""
    console.print("[bold]AI 분석 시작...[/bold]")
    agent = GlobalEconAgent()
    report = agent.analyze_existing(date)
    _print_report_summary(report, get_settings().reports_dir)


@app.command(name="schedule")
def schedule_cmd() -> None:
    """매일 자동 실행 스케줄러 시작."""
    settings = get_settings()
    console.print(Panel.fit(
        f"매일 [bold]{settings.schedule_hour:02d}:{settings.schedule_minute:02d}[/bold] "
        f"({settings.timezone})에 자동 실행",
        title="스케줄러",
        border_style="green",
    ))
    start_scheduler()


@app.command()
def status() -> None:
    """에이전트 상태 확인."""
    settings = get_settings()
    from global_econ_agent.storage.database import Database

    db = Database(settings)
    articles = db.get_recent_articles(hours=48, limit=5)

    table = Table(title="에이전트 상태")
    table.add_column("항목")
    table.add_column("값")
    table.add_row("버전", __version__)
    table.add_row("DB 경로", str(settings.db_path))
    table.add_row("보고서 경로", str(settings.reports_dir))
    table.add_row("OpenAI API", "✓ 설정됨" if settings.openai_api_key else "✗ 미설정")
    table.add_row("NewsAPI", "✓ 설정됨" if settings.newsapi_key else "✗ 미설정")
    table.add_row("최근 48h 기사", f"{len(articles)}건+")
    table.add_row("스케줄", f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d} {settings.timezone}")
    console.print(table)


def _print_report_summary(report, reports_dir: Path) -> None:
    console.print()
    console.print(Panel.fit(
        f"[bold green]보고서 생성 완료[/bold green]\n\n"
        f"날짜: {report.report_date}\n"
        f"수집: {report.articles_collected}건 | 분석: {report.articles_analyzed}건\n"
        f"핵심 이슈: {len(report.key_issues)}건 | 시나리오: {len(report.scenarios)}개",
        border_style="green",
    ))

    if report.key_issues:
        table = Table(title="주요 이슈")
        table.add_column("#", style="dim")
        table.add_column("영향도")
        table.add_column("제목")
        for i, issue in enumerate(report.key_issues[:5], 1):
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.impact_level.value, "⚪")
            table.add_row(str(i), emoji, issue.title[:50])
        console.print(table)

    report_path = reports_dir / f"report_{report.report_date}.md"
    if report_path.exists():
        console.print(f"\n📄 보고서: [underline]{report_path}[/underline]")


if __name__ == "__main__":
    app()
