import logging
from pathlib import Path

import yaml

from global_econ_agent.collectors.base import BaseCollector
from global_econ_agent.collectors.rss_collector import NewsAPICollector, RSSCollector
from global_econ_agent.config import Settings, get_settings

logger = logging.getLogger(__name__)


def build_collectors(settings: Settings | None = None) -> list[BaseCollector]:
    settings = settings or get_settings()
    collectors: list[BaseCollector] = []

    sources_path = settings.news_sources_yaml
    if not sources_path.exists():
        logger.warning("뉴스 소스 설정 파일 없음: %s", sources_path)
        return collectors

    with open(sources_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        source_type = source.get("type", "rss")
        if source_type == "rss" and source.get("url"):
            collectors.append(
                RSSCollector(
                    source_id=source["id"],
                    source_name=source["name"],
                    url=source["url"],
                    region=source.get("region", "GLOBAL"),
                )
            )

    if settings.newsapi_key:
        for query_cfg in config.get("newsapi_queries", []):
            collectors.append(
                NewsAPICollector(
                    api_key=settings.newsapi_key,
                    query=query_cfg["query"],
                    region=query_cfg.get("region", "GLOBAL"),
                )
            )
    else:
        logger.info("NEWSAPI_KEY 미설정 — NewsAPI 수집 건너뜀")

    logger.info("수집기 %d개 초기화 완료", len(collectors))
    return collectors


def collect_all(settings: Settings | None = None) -> list:
    from global_econ_agent.models.schemas import Article

    settings = settings or get_settings()
    all_articles: list[Article] = []
    seen_urls: set[str] = set()

    for collector in build_collectors(settings):
        try:
            for article in collector.collect():
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    all_articles.append(article)
        except Exception as e:
            logger.error("수집기 오류 [%s]: %s", collector.name, e)

    logger.info("전체 수집 완료: %d건 (중복 제거 후)", len(all_articles))
    return all_articles
