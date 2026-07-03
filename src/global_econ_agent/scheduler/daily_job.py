import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from global_econ_agent.agent import GlobalEconAgent
from global_econ_agent.config import get_settings

logger = logging.getLogger(__name__)


def run_scheduled_job() -> None:
    """스케줄러에서 호출되는 일일 작업."""
    logger.info("스케줄된 일일 작업 시작")
    agent = GlobalEconAgent()
    report, _outputs = agent.run_daily_pipeline()
    logger.info("스케줄된 작업 완료: %s", report.report_date)


def start_scheduler() -> None:
    """매일 지정 시각에 파이프라인 실행."""
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.timezone)

    trigger = CronTrigger(
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        timezone=settings.timezone,
    )

    scheduler.add_job(
        run_scheduled_job,
        trigger=trigger,
        id="daily_econ_report",
        name="일일 글로벌 경제 보고서 생성",
        replace_existing=True,
    )

    logger.info(
        "스케줄러 시작 — 매일 %02d:%02d (%s)",
        settings.schedule_hour,
        settings.schedule_minute,
        settings.timezone,
    )
    print(f"⏰ 스케줄러 실행 중 — 매일 {settings.schedule_hour:02d}:{settings.schedule_minute:02d} ({settings.timezone})")
    print("   Ctrl+C로 종료")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료")
