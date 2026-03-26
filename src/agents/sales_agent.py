import anthropic

from src.agents.base import BaseAgent
from src.agents.prompts.sales_system import build_sales_system_prompt
from src.ralph.strategy import Strategy


class SalesAgent(BaseAgent):
    """AI 판매 에이전트 - 영업 전략을 실행합니다."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
        product_name: str = "",
        product_description: str = "",
        product_price: str = "",
        strategy: Strategy | None = None,
    ):
        super().__init__(client=client, model=model)
        self.product_name = product_name
        self.product_description = product_description
        self.product_price = product_price
        self.strategy = strategy

    def build_system_prompt(self) -> str:
        return build_sales_system_prompt(
            product_name=self.product_name,
            product_description=self.product_description,
            product_price=self.product_price,
            strategy=self.strategy,
        )

    @property
    def role(self) -> str:
        return "sales"
