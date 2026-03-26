from pathlib import Path

import yaml

from src.personas.schema import Persona


def load_personas(path: str | Path = "config/personas.yaml") -> list[Persona]:
    """YAML 파일에서 페르소나 목록을 로드합니다."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return [Persona(**p) for p in data["personas"]]


def get_persona_by_id(personas: list[Persona], persona_id: str) -> Persona | None:
    """ID로 특정 페르소나를 조회합니다."""
    for p in personas:
        if p.id == persona_id:
            return p
    return None
