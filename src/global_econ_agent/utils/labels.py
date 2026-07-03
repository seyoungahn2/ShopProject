from global_econ_agent.models.schemas import Category, ImpactLevel, Region

CATEGORY_LABELS: dict[Category, str] = {
    Category.POLITICS: "정치",
    Category.ECONOMY: "경제",
    Category.INTEREST_RATES: "금리",
    Category.CONFLICT: "전쟁/분쟁",
    Category.COMMODITIES: "원자재",
    Category.FX: "환율",
    Category.TRADE: "무역",
    Category.DISASTER: "재난/재해",
    Category.TERRORISM: "테러/안보",
    Category.CORPORATE: "기업/주가",
    Category.OTHER: "기타",
}

REGION_LABELS: dict[Region, str] = {
    Region.US: "미국",
    Region.KR: "한국",
    Region.JP: "일본",
    Region.GLOBAL: "글로벌",
}

IMPACT_LABELS: dict[ImpactLevel, str] = {
    ImpactLevel.HIGH: "높음",
    ImpactLevel.MEDIUM: "보통",
    ImpactLevel.LOW: "낮음",
}


def category_label(category: Category) -> str:
    return CATEGORY_LABELS.get(category, category.value)


def region_label(region: Region) -> str:
    return REGION_LABELS.get(region, region.value)


def impact_label(level: ImpactLevel) -> str:
    return IMPACT_LABELS.get(level, level.value)
