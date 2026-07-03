import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from global_econ_agent.config import Settings, get_settings
from global_econ_agent.models.schemas import Article, Category, DailyReport, Region

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class ArticleRecord(Base):
    __tablename__ = "articles"

    id = Column(String(32), primary_key=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, default="")
    url = Column(String(1000), unique=True, nullable=False)
    source_id = Column(String(100))
    source_name = Column(String(200))
    region = Column(String(20), default="GLOBAL")
    published_at = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    categories = Column(Text, default="[]")
    relevance_score = Column(Float, default=0.0)
    is_key_issue = Column(Boolean, default=False)


class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(String(20), unique=True, nullable=False)
    content_json = Column(Text, nullable=False)
    markdown_path = Column(String(500))
    generated_at = Column(DateTime, default=datetime.utcnow)


class Database:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.engine = create_engine(f"sqlite:///{self.settings.db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def save_articles(self, articles: list[Article]) -> int:
        saved = 0
        with self.SessionLocal() as session:
            for article in articles:
                if self._upsert_article(session, article):
                    saved += 1
            session.commit()
        logger.info("DB 저장: %d건", saved)
        return saved

    def _upsert_article(self, session: Session, article: Article) -> bool:
        existing = session.execute(
            select(ArticleRecord).where(ArticleRecord.url == article.url)
        ).scalar_one_or_none()

        categories_json = json.dumps([c.value for c in article.categories])

        if existing:
            existing.title = article.title
            existing.summary = article.summary
            existing.categories = categories_json
            existing.relevance_score = article.relevance_score
            existing.is_key_issue = article.is_key_issue
            return False

        record = ArticleRecord(
            id=article.id or article.url[:32],
            title=article.title,
            summary=article.summary,
            url=article.url,
            source_id=article.source_id,
            source_name=article.source_name,
            region=article.region.value,
            published_at=article.published_at,
            collected_at=article.collected_at,
            categories=categories_json,
            relevance_score=article.relevance_score,
            is_key_issue=article.is_key_issue,
        )
        session.add(record)
        return True

    def get_recent_articles(self, hours: int = 48, limit: int = 100) -> list[Article]:
        cutoff = datetime.utcnow()
        from datetime import timedelta

        cutoff = cutoff - timedelta(hours=hours)

        with self.SessionLocal() as session:
            records = session.execute(
                select(ArticleRecord)
                .where(ArticleRecord.collected_at >= cutoff)
                .order_by(ArticleRecord.relevance_score.desc(), ArticleRecord.collected_at.desc())
                .limit(limit)
            ).scalars().all()

        return [_record_to_article(r) for r in records]

    def update_article(self, article: Article) -> None:
        with self.SessionLocal() as session:
            record = session.get(ArticleRecord, article.id)
            if record:
                record.categories = json.dumps([c.value for c in article.categories])
                record.relevance_score = article.relevance_score
                record.is_key_issue = article.is_key_issue
                session.commit()

    def save_report(self, report: DailyReport, markdown_path: str) -> None:
        with self.SessionLocal() as session:
            existing = session.execute(
                select(ReportRecord).where(ReportRecord.report_date == report.report_date)
            ).scalar_one_or_none()

            content = report.model_dump_json()

            if existing:
                existing.content_json = content
                existing.markdown_path = markdown_path
                existing.generated_at = datetime.utcnow()
            else:
                session.add(
                    ReportRecord(
                        report_date=report.report_date,
                        content_json=content,
                        markdown_path=markdown_path,
                    )
                )
            session.commit()

    def get_report(self, report_date: str) -> Optional[DailyReport]:
        with self.SessionLocal() as session:
            record = session.execute(
                select(ReportRecord).where(ReportRecord.report_date == report_date)
            ).scalar_one_or_none()
            if record:
                return DailyReport.model_validate_json(record.content_json)
        return None


def _record_to_article(record: ArticleRecord) -> Article:
    categories = []
    try:
        cat_values = json.loads(record.categories or "[]")
        valid_categories = {c.value for c in Category}
        categories = [Category(c) for c in cat_values if c in valid_categories]
    except (json.JSONDecodeError, ValueError):
        pass

    return Article(
        id=record.id,
        title=record.title,
        summary=record.summary or "",
        url=record.url,
        source_id=record.source_id or "",
        source_name=record.source_name or "",
        region=Region(record.region) if record.region in Region.__members__ else Region.GLOBAL,
        published_at=record.published_at,
        collected_at=record.collected_at,
        categories=categories,
        relevance_score=record.relevance_score or 0.0,
        is_key_issue=record.is_key_issue or False,
    )
