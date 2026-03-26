from abc import ABC, abstractmethod

import anthropic

from src.conversation.turn import Turn


class BaseAgent(ABC):
    """모든 에이전트의 기반 클래스"""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
        system_prompt: str = "",
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt

    @abstractmethod
    def build_system_prompt(self) -> str:
        """에이전트별 시스템 프롬프트를 생성합니다."""
        ...

    async def respond(self, conversation_history: list[Turn]) -> str:
        """대화 이력을 기반으로 응답을 생성합니다."""
        messages = self._build_messages(conversation_history)
        system = self.build_system_prompt()

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def _build_messages(self, history: list[Turn]) -> list[dict]:
        """Turn 리스트를 Claude API 메시지 포맷으로 변환합니다."""
        messages = []
        for turn in history:
            role = "assistant" if turn.speaker == self.role else "user"
            messages.append({"role": role, "content": turn.content})
        return messages

    @property
    @abstractmethod
    def role(self) -> str:
        """에이전트의 역할 식별자 (sales / customer)"""
        ...
