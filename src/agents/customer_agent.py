import anthropic

from src.agents.base import BaseAgent
from src.agents.prompts.customer_system import build_customer_system_prompt
from src.personas.schema import Persona


class CustomerAgent(BaseAgent):
    """AI 고객 에이전트 - 페르소나 기반으로 반응합니다."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
        persona: Persona | None = None,
    ):
        super().__init__(client=client, model=model)
        self.persona = persona

    def build_system_prompt(self) -> str:
        if self.persona is None:
            raise ValueError("CustomerAgent requires a persona")
        return build_customer_system_prompt(self.persona)

    @property
    def role(self) -> str:
        return "customer"
