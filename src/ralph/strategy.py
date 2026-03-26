from datetime import datetime

from pydantic import BaseModel, Field


class Strategy(BaseModel):
    """영업 전략 정의"""

    id: str = Field(..., description="전략 고유 ID")
    name: str = Field(..., description="전략명")
    approach: str = Field(..., description="전반적 접근 방식")
    opening_style: str = Field(..., description="오프닝 스타일")
    persuasion_tactics: list[str] = Field(default_factory=list, description="설득 기법 목록")
    objection_handling: str = Field(default="", description="반론 대응 방식")
    target_personas: list[str] = Field(
        default_factory=list, description="특히 효과적일 페르소나 유형"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    iteration: int = Field(default=0, description="RALPH 반복 회차")


class StrategyResult(BaseModel):
    """전략 실행 결과 요약"""

    strategy_id: str
    iteration: int
    avg_weighted_score: float
    conversation_count: int
    purchase_count: int = 0
    wishlist_count: int = 0
    exit_count: int = 0
    purchase_rate: float = 0.0
    total_revenue: float = 0.0
    best_persona_types: list[str] = Field(default_factory=list)
    worst_persona_types: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
