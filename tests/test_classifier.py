import pytest

from global_econ_agent.models.schemas import Article, Category, Region
from global_econ_agent.processors.classifier import ArticleClassifier, ArticleDeduplicator


@pytest.fixture
def classifier():
    return ArticleClassifier()


def test_classify_interest_rate_article(classifier):
    article = Article(
        title="Fed signals potential rate cut in September FOMC meeting",
        summary="The Federal Reserve indicated it may cut interest rates.",
        url="https://example.com/1",
        source_id="test",
        source_name="Test",
        region=Region.US,
    )
    result = classifier.classify(article)
    assert Category.INTEREST_RATES in result.categories
    assert result.relevance_score > 0


def test_classify_korean_article(classifier):
    article = Article(
        title="한국은행, 기준금리 동결 결정",
        summary="한국은행이 기준금리를 3.5%로 동결했습니다.",
        url="https://example.com/2",
        source_id="test",
        source_name="Test",
        region=Region.KR,
    )
    result = classifier.classify(article)
    assert Category.INTEREST_RATES in result.categories


def test_deduplicate_similar_titles():
    dedup = ArticleDeduplicator()
    articles = [
        Article(
            title="Oil prices surge on OPEC cuts",
            url="https://example.com/a",
            source_id="t",
            source_name="T",
            relevance_score=5.0,
        ),
        Article(
            title="Oil prices surge on OPEC production cuts",
            url="https://example.com/b",
            source_id="t",
            source_name="T",
            relevance_score=3.0,
        ),
        Article(
            title="Japan Nikkei hits record high",
            url="https://example.com/c",
            source_id="t",
            source_name="T",
            relevance_score=4.0,
        ),
    ]
    result = dedup.deduplicate(articles)
    assert len(result) == 2
    assert result[0].title.startswith("Oil prices")


def test_fallback_analysis_without_api_key():
    from global_econ_agent.analyzers.impact_analyzer import ImpactAnalyzer
    from global_econ_agent.config import Settings

    settings = Settings(openai_api_key="")
    analyzer = ImpactAnalyzer(settings)
    articles = [
        Article(
            title="US Treasury yields rise",
            url="https://example.com/d",
            source_id="t",
            source_name="T",
            region=Region.US,
            categories=[Category.INTEREST_RATES],
            relevance_score=6.0,
        )
    ]
    results = analyzer.analyze_articles(articles, top_n=1)
    assert len(results) == 1
    assert results[0].stock_impact
