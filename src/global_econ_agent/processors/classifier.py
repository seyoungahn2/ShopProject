import logging
import re
from pathlib import Path

import yaml

from global_econ_agent.models.schemas import Article, Category, Region

logger = logging.getLogger(__name__)

# 지역별 키워드
REGION_KEYWORDS: dict[Region, list[str]] = {
    Region.US: [
        "us", "usa", "america", "american", "fed", "fomc", "wall street",
        "s&p", "nasdaq", "treasury", "미국", "연준",
    ],
    Region.KR: [
        "korea", "korean", "south korea", "kospi", "kosdaq", "bok",
        "한국", "코스피", "코스닥", "한국은행", "원화",
    ],
    Region.JP: [
        "japan", "japanese", "nikkei", "topix", "boj", "yen",
        "일본", "엔화", "닛케이",
    ],
}


class ArticleClassifier:
    def __init__(self, config_path: Path | None = None):
        self.category_keywords: dict[Category, list[str]] = {}
        if config_path and config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            for cat in config.get("categories", []):
                try:
                    category = Category(cat["id"])
                    self.category_keywords[category] = [
                        kw.lower() for kw in cat.get("keywords", [])
                    ]
                except ValueError:
                    pass

        if not self.category_keywords:
            self._load_defaults()

    def _load_defaults(self) -> None:
        self.category_keywords = {
            Category.POLITICS: ["election", "policy", "government", "정치"],
            Category.ECONOMY: ["gdp", "inflation", "economy", "경제", "물가"],
            Category.INTEREST_RATES: ["fed", "fomc", "rate", "금리", "boj", "bok"],
            Category.CONFLICT: ["war", "conflict", "military", "전쟁", "분쟁"],
            Category.COMMODITIES: ["oil", "gold", "commodity", "원유", "원자재"],
            Category.FX: ["dollar", "yen", "won", "forex", "환율"],
            Category.TRADE: ["tariff", "trade", "export", "무역", "관세"],
            Category.DISASTER: ["earthquake", "flood", "typhoon", "지진", "재해"],
            Category.TERRORISM: ["terror", "attack", "security", "테러"],
            Category.CORPORATE: ["earnings", "stock", "ipo", "실적", "주가"],
        }

    def classify(self, article: Article) -> Article:
        text = f"{article.title} {article.summary}".lower()
        matched: list[Category] = []

        for category, keywords in self.category_keywords.items():
            for kw in keywords:
                if kw in text:
                    matched.append(category)
                    break

        if not matched:
            matched = [Category.OTHER]

        article.categories = list(dict.fromkeys(matched))
        article.relevance_score = self._score_relevance(article, text)
        return article

    def _score_relevance(self, article: Article, text: str) -> float:
        score = 0.0

        # 카테고리 수
        score += len(article.categories) * 0.5

        # 핵심 카테고리 가중치
        high_impact = {Category.INTEREST_RATES, Category.CONFLICT, Category.FX, Category.TRADE}
        score += sum(2.0 for c in article.categories if c in high_impact)

        # 지역 매칭
        for region, keywords in REGION_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                score += 1.0
        if article.region != Region.GLOBAL:
            score += 1.5

        # 제목 길이/품질
        if len(article.title) > 20:
            score += 0.5

        return round(score, 2)

    def classify_batch(self, articles: list[Article]) -> list[Article]:
        return [self.classify(a) for a in articles]


class ArticleDeduplicator:
    def deduplicate(self, articles: list[Article], similarity_threshold: float = 0.85) -> list[Article]:
        if not articles:
            return []

        unique: list[Article] = []
        seen_titles: list[str] = []

        sorted_articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)

        for article in sorted_articles:
            normalized = _normalize_title(article.title)
            is_dup = False
            for seen in seen_titles:
                if _title_similarity(normalized, seen) >= similarity_threshold:
                    is_dup = True
                    break
            if not is_dup:
                seen_titles.append(normalized)
                unique.append(article)

        return unique


def _normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    return re.sub(r"\s+", " ", title).strip()


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
