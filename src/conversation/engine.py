import uuid
from datetime import datetime

from src.conversation.rules import check_termination
from src.conversation.turn import ConversationSession, Turn


class ConversationEngine:
    """Sales Agent와 Customer Agent 간 턴 기반 대화를 오케스트레이션합니다.

    customer_agent는 BaseAgent이든 RuleCustomerAgent이든
    respond(conversation_history) 메서드만 있으면 동작합니다.
    """

    def __init__(self, max_turns: int = 16):
        self.max_turns = max_turns

    async def run(
        self,
        sales_agent,
        customer_agent,
        persona_id: str = "",
        strategy_id: str = "",
        product_name: str = "",
    ) -> ConversationSession:
        """대화를 실행하고 완료된 세션을 반환합니다."""

        session = ConversationSession(
            session_id=str(uuid.uuid4()),
            persona_id=persona_id,
            strategy_id=strategy_id,
            product_name=product_name,
        )

        termination_reason = "max_turns"

        for turn_num in range(self.max_turns):
            # Sales Agent가 먼저 발화 (짝수 턴)
            if turn_num % 2 == 0:
                speaker = "sales"
                response = await sales_agent.respond(session.turns)
            else:
                speaker = "customer"
                response = await customer_agent.respond(session.turns)

            turn = Turn(
                speaker=speaker,
                content=response,
                turn_number=turn_num + 1,
            )
            session.turns.append(turn)

            # 고객 발화 후 종료 조건 확인
            if speaker == "customer":
                term = check_termination(response)
                if term is not None:
                    termination_reason = term
                    break

        session.termination_reason = termination_reason
        session.ended_at = datetime.now()
        return session
