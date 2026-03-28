"""Plan 단계: 페르소나 선택 (전체 사용)"""

from src.personas.schema import EVPersona


def select_personas(all_personas: list[EVPersona], **_kwargs) -> list[EVPersona]:
    """매 이터레이션 전체 2,000명 사용 — 선택 로직 불필요."""
    return all_personas
