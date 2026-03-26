from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    """단일 평가 차원의 점수"""

    name: str
    score: float = Field(..., ge=1, le=10, description="1~10 점수")
    reasoning: str = Field(default="", description="점수 근거")


class EvaluationResult(BaseModel):
    """대화 세션의 다차원 평가 결과"""

    session_id: str
    interest_level: DimensionScore = Field(..., description="관심도")
    conversation_continuation: DimensionScore = Field(..., description="대화 지속도")
    emotional_change: DimensionScore = Field(..., description="감정 변화")
    purchase_intent: DimensionScore = Field(..., description="구매 의향")
    final_outcome: DimensionScore = Field(..., description="최종 행동 결과")
    overall_summary: str = Field(default="", description="종합 평가 요약")

    @property
    def weighted_score(self) -> float:
        """가중 종합 점수를 계산합니다."""
        weights = {
            "interest_level": 0.20,
            "conversation_continuation": 0.15,
            "emotional_change": 0.20,
            "purchase_intent": 0.25,
            "final_outcome": 0.20,
        }
        total = 0.0
        for name, weight in weights.items():
            dim: DimensionScore = getattr(self, name)
            total += dim.score * weight
        return round(total, 2)

    @property
    def scores_dict(self) -> dict[str, float]:
        return {
            "interest_level": self.interest_level.score,
            "conversation_continuation": self.conversation_continuation.score,
            "emotional_change": self.emotional_change.score,
            "purchase_intent": self.purchase_intent.score,
            "final_outcome": self.final_outcome.score,
            "weighted_total": self.weighted_score,
        }
