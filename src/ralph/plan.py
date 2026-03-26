import random

from src.personas.schema import Persona


def select_personas(
    all_personas: list[Persona],
    count: int = 20,
    focus_types: list[str] | None = None,
) -> list[Persona]:
    """이번 반복에 사용할 페르소나를 선택합니다.

    focus_types가 주어지면 해당 유형의 페르소나를 우선 포함합니다.
    """
    if count >= len(all_personas):
        return all_personas

    selected: list[Persona] = []

    # 포커스 유형 우선 선택
    if focus_types:
        for persona in all_personas:
            if any(
                ft in persona.reaction_pattern.value
                or ft in persona.purchase_tendency.value
                or ft in persona.generation.value
                for ft in focus_types
            ):
                selected.append(persona)

    # 나머지는 랜덤 채우기
    remaining = [p for p in all_personas if p not in selected]
    random.shuffle(remaining)

    while len(selected) < count and remaining:
        selected.append(remaining.pop())

    return selected[:count]
