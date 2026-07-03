import re

from global_econ_agent.models.schemas import TermGlossary

# 자주 쓰이는 금융·경제 용어 (원어 → 한글 해석)
BUILTIN_TERMS: dict[str, str] = {
    "Fed": "연방준비제도 — 미국 중앙은행",
    "FOMC": "연방공개시장위원회 — 미국 금리를 결정하는 기구",
    "Federal Reserve": "연방준비제도 — 미국 중앙은행",
    "BOJ": "일본은행 — 일본 중앙은행",
    "BOK": "한국은행 — 대한민국 중앙은행",
    "Bank of Japan": "일본은행 — 일본 중앙은행",
    "Bank of Korea": "한국은행 — 대한민국 중앙은행",
    "S&P 500": "S&P 500 — 미국 대형주 500개 종목 지수",
    "NASDAQ": "나스닥 — 미국 기술주 중심 주가지수",
    "KOSPI": "코스피 — 한국 종합주가지수",
    "KOSDAQ": "코스닥 — 한국 중소·벤처 기업 주가지수",
    "Nikkei": "닛케이 — 일본 대표 주가지수",
    "TOPIX": "토픽스 — 일본 전체 시가총액 기준 지수",
    "JGB": "일본국채 — 일본 정부가 발행하는 채권",
    "Treasury": "미국 국채 — 미국 정부가 발행하는 채권",
    "yield": "수익률 — 채권 투자 시 기대되는 이자 수익 비율",
    "rate cut": "금리 인하 — 기준금리를 낮추는 정책",
    "rate hike": "금리 인상 — 기준금리를 올리는 정책",
    "inflation": "인플레이션 — 물가가 지속적으로 오르는 현상",
    "recession": "경기 침체 — 경제 활동이 장기간 위축되는 상태",
    "tariff": "관세 — 수입품에 부과하는 세금",
    "sanction": "제재 — 특정 국가·기관에 대한 경제적 제한 조치",
    "OPEC": "오펙 — 주요 산유국 협의체",
    "safe haven": "안전자산 — 불확실성 증가 시 자금이 몰리는 자산",
    "risk-off": "위험회피 — 투자자가 위험 자산을 줄이고 안전자산을 선호하는 심리",
    "risk-on": "위험선호 — 투자자가 주식 등 위험 자산을 적극 매수하는 심리",
    "stagflation": "스태그플레이션 — 경기 침체와 인플레이션이 동시에 나타나는 현상",
    "quantitative easing": "양적완화 — 중앙은행이 채권을 대량 매입해 시중에 돈을 푸는 정책",
    "QE": "양적완화 — 중앙은행의 채권 대량 매입 정책",
    "hawkish": "매파적 — 금리 인상 등 긴축 정책을 선호하는 입장",
    "dovish": "비둘기파 — 금리 인하 등 완화 정책을 선호하는 입장",
    "IPO": "기업공개 — 기업이 주식시장에 처음 상장하는 것",
    "earnings": "실적 — 기업의 분기·연간 수익 결과",
    "stress test": "스트레스 테스트 — 은행이 경제 충격 상황에서 버틸 수 있는지 검사하는 제도",
    "duration": "듀레이션 — 채권 가격이 금리 변동에 얼마나 민감한지 나타내는 지표",
    "forex": "외환 — 외국 통화 거래 시장",
    "FX": "외환 — 외국 통화 거래",
    "LNG": "액화천연가스 — 천연가스를 액체 상태로 운반·저장하는 형태",
    "WTI": "서부텍사스산 원유 — 미국 원유 가격의 기준 지표",
    "Brent": "브렌트유 — 국제 원유 가격의 기준 지표",
}


def extract_glossary(text: str, extra_terms: list[TermGlossary] | None = None) -> list[TermGlossary]:
    """텍스트에서 알려진 원어 용어를 찾아 한글 해석을 붙입니다."""
    found: dict[str, str] = {}
    text_lower = text.lower()

    # 긴 용어부터 매칭 (부분 중복 방지)
    for term, meaning in sorted(BUILTIN_TERMS.items(), key=lambda x: len(x[0]), reverse=True):
        if term.lower() in text_lower:
            found[term] = meaning

    if extra_terms:
        for item in extra_terms:
            found[item.term] = item.meaning_ko

    return [TermGlossary(term=k, meaning_ko=v) for k, v in found.items()]


def merge_glossaries(*glossaries: list[TermGlossary]) -> list[TermGlossary]:
    """여러 용어집을 합치고 중복을 제거합니다 (먼저 등장한 해석 우선)."""
    merged: dict[str, str] = {}
    for glossary in glossaries:
        for item in glossary:
            if item.term not in merged:
                merged[item.term] = item.meaning_ko
    return [TermGlossary(term=k, meaning_ko=v) for k, v in sorted(merged.items())]


def format_glossary_inline(glossary: list[TermGlossary]) -> str:
    """보고서 본문에 삽입할 인라인 용어 해석 문자열."""
    if not glossary:
        return ""
    lines = [f"- **{g.term}**: {g.meaning_ko}" for g in glossary]
    return "\n".join(lines)
