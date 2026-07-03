from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Region(str, Enum):
    US = "US"
    KR = "KR"
    JP = "JP"
    GLOBAL = "GLOBAL"


class Category(str, Enum):
    POLITICS = "politics"
    ECONOMY = "economy"
    INTEREST_RATES = "interest_rates"
    CONFLICT = "conflict"
    COMMODITIES = "commodities"
    FX = "fx"
    TRADE = "trade"
    DISASTER = "disaster"
    TERRORISM = "terrorism"
    CORPORATE = "corporate"
    OTHER = "other"


class ImpactLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TermGlossary(BaseModel):
    """원어 용어와 한글 해석."""
    term: str
    meaning_ko: str


class Article(BaseModel):
    id: Optional[str] = None
    title: str
    summary: str = ""
    url: str
    source_id: str
    source_name: str
    region: Region = Region.GLOBAL
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    categories: list[Category] = Field(default_factory=list)
    relevance_score: float = 0.0
    is_key_issue: bool = False


class ImpactAnalysis(BaseModel):
    article_id: str
    title_ko: str
    title_original: str = ""
    categories: list[Category]
    regions_affected: list[Region]
    impact_level: ImpactLevel
    stock_impact: str
    bond_impact: str
    rate_outlook: str
    affected_sectors: list[str] = Field(default_factory=list)
    affected_companies: list[str] = Field(default_factory=list)
    summary_ko: str
    term_glossary: list[TermGlossary] = Field(default_factory=list)

    @property
    def title(self) -> str:
        """하위 호환용 — 한글 제목 우선."""
        return self.title_ko or self.title_original


class Scenario(BaseModel):
    name: str
    probability: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    us_market_outlook: str
    kr_market_outlook: str
    jp_market_outlook: str
    rate_outlook: str
    key_risks: list[str] = Field(default_factory=list)
    investment_implications: str
    term_glossary: list[TermGlossary] = Field(default_factory=list)


class DailyReport(BaseModel):
    report_date: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    executive_summary: str
    key_issues: list[ImpactAnalysis] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    term_glossary: list[TermGlossary] = Field(default_factory=list)
    market_snapshot: dict = Field(default_factory=dict)
    articles_collected: int = 0
    articles_analyzed: int = 0
