import json

import anthropic

from src.conversation.turn import ConversationSession
from src.evaluation.dimensions import get_evaluation_prompt
from src.evaluation.schema import DimensionScore, EvaluationResult


class Evaluator:
    """대화 세션을 다차원으로 평가합니다. (LLM-as-Judge)"""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.client = client
        self.model = model

    async def evaluate(self, session: ConversationSession) -> EvaluationResult:
        """대화 세션을 평가하고 5차원 점수를 반환합니다."""

        prompt = get_evaluation_prompt(session.transcript)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text

        # JSON 파싱 (코드블록 제거)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        data = json.loads(cleaned)

        return EvaluationResult(
            session_id=session.session_id,
            interest_level=DimensionScore(name="interest_level", **data["interest_level"]),
            conversation_continuation=DimensionScore(
                name="conversation_continuation", **data["conversation_continuation"]
            ),
            emotional_change=DimensionScore(name="emotional_change", **data["emotional_change"]),
            purchase_intent=DimensionScore(name="purchase_intent", **data["purchase_intent"]),
            final_outcome=DimensionScore(name="final_outcome", **data["final_outcome"]),
            overall_summary=data.get("overall_summary", ""),
        )
