import hashlib
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from global_econ_agent.collectors.base import BaseCollector
from global_econ_agent.models.schemas import Article, Region

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str,
        region: str = "GLOBAL",
        timeout: float = 15.0,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.url = url
        self.region = Region(region) if region in Region.__members__ else Region.GLOBAL
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"RSS:{self.source_name}"

    def collect(self) -> list[Article]:
        articles: list[Article] = []
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(
                    self.url,
                    headers={"User-Agent": "GlobalEconAgent/0.1 (+https://github.com)"},
                )
                response.raise_for_status()
                feed = feedparser.parse(response.text)
        except Exception as e:
            logger.warning("RSS 수집 실패 [%s]: %s", self.source_name, e)
            return articles

        for entry in feed.entries[:30]:
            article = self._parse_entry(entry)
            if article:
                articles.append(article)

        logger.info("RSS 수집 완료 [%s]: %d건", self.source_name, len(articles))
        return articles

    def _parse_entry(self, entry: Any) -> Article | None:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            return None

        summary = ""
        if hasattr(entry, "summary"):
            summary = _strip_html(entry.summary)[:500]
        elif hasattr(entry, "description"):
            summary = _strip_html(entry.description)[:500]

        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        elif hasattr(entry, "published"):
            try:
                published_at = parsedate_to_datetime(entry.published)
            except (TypeError, ValueError):
                pass

        article_id = hashlib.sha256(f"{self.source_id}:{link}".encode()).hexdigest()[:16]

        return Article(
            id=article_id,
            title=title,
            summary=summary,
            url=link,
            source_id=self.source_id,
            source_name=self.source_name,
            region=self.region,
            published_at=published_at,
        )


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text).strip()


class NewsAPICollector(BaseCollector):
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str, query: str, region: str = "GLOBAL", source_label: str = "NewsAPI"):
        self.api_key = api_key
        self.query = query
        self.region = Region(region) if region in Region.__members__ else Region.GLOBAL
        self.source_label = source_label

    @property
    def name(self) -> str:
        return f"NewsAPI:{self.query[:30]}"

    def collect(self) -> list[Article]:
        if not self.api_key:
            return []

        articles: list[Article] = []
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    self.BASE_URL,
                    params={
                        "q": self.query,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 20,
                        "apiKey": self.api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.warning("NewsAPI 수집 실패 [%s]: %s", self.query[:40], e)
            return articles

        for item in data.get("articles", []):
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            if not title or not url or title == "[Removed]":
                continue

            published_at = None
            if item.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            article_id = hashlib.sha256(f"newsapi:{url}".encode()).hexdigest()[:16]
            source_name = item.get("source", {}).get("name", self.source_label)

            articles.append(
                Article(
                    id=article_id,
                    title=title,
                    summary=(item.get("description") or "")[:500],
                    url=url,
                    source_id=f"newsapi_{hashlib.md5(self.query.encode()).hexdigest()[:8]}",
                    source_name=source_name,
                    region=self.region,
                    published_at=published_at,
                )
            )

        logger.info("NewsAPI 수집 완료 [%s]: %d건", self.query[:40], len(articles))
        return articles
