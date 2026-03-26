from datetime import datetime

from pydantic import BaseModel, Field


class Turn(BaseModel):
    """대화의 한 턴을 나타냅니다."""

    speaker: str = Field(..., description="발화자 (sales / customer)")
    content: str = Field(..., description="발화 내용")
    turn_number: int = Field(..., description="턴 번호")
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationSession(BaseModel):
    """하나의 완료된 대화 세션"""

    session_id: str = Field(..., description="세션 고유 ID")
    persona_id: str = Field(..., description="고객 페르소나 ID")
    strategy_id: str = Field(default="", description="사용된 전략 ID")
    product_name: str = Field(default="", description="판매 제품명")
    turns: list[Turn] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None
    termination_reason: str = Field(
        default="max_turns", description="종료 사유 (max_turns / customer_exit / purchase / timeout)"
    )

    @property
    def total_turns(self) -> int:
        return len(self.turns)

    @property
    def transcript(self) -> str:
        """전체 대화를 텍스트로 반환합니다."""
        lines = []
        for turn in self.turns:
            label = "판매원" if turn.speaker == "sales" else "고객"
            lines.append(f"[{label}] {turn.content}")
        return "\n".join(lines)
