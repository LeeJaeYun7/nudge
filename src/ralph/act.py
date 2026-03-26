import asyncio

from openai import AsyncOpenAI

from src.agents.rule_customer import RuleCustomerAgent
from src.agents.sales_agent import SalesAgent
from src.conversation.engine import ConversationEngine
from src.conversation.turn import ConversationSession
from src.personas.schema import Persona
from src.ralph.strategy import Strategy


async def execute_strategy(
    client: AsyncOpenAI,
    model: str,
    strategy: Strategy,
    personas: list[Persona],
    product_name: str,
    product_description: str,
    product_price: str,
    max_turns: int = 16,
    concurrency: int = 50,
    on_progress: callable = None,
) -> list[ConversationSession]:
    """전략을 여러 페르소나 대상으로 실행합니다.

    Customer는 규칙 기반으로 동작하여 LLM 비용을 절감합니다.
    """

    engine = ConversationEngine(max_turns=max_turns)
    semaphore = asyncio.Semaphore(concurrency)
    completed = 0

    async def run_one(persona: Persona) -> ConversationSession:
        nonlocal completed
        async with semaphore:
            sales = SalesAgent(
                client=client,
                model=model,
                product_name=product_name,
                product_description=product_description,
                product_price=product_price,
                strategy=strategy,
            )
            customer = RuleCustomerAgent(persona=persona)
            session = await engine.run(
                sales_agent=sales,
                customer_agent=customer,
                persona_id=persona.id,
                strategy_id=strategy.id,
                product_name=product_name,
            )
            completed += 1
            if on_progress:
                on_progress(completed, len(personas))
            return session

    sessions = await asyncio.gather(*[run_one(p) for p in personas])
    return list(sessions)
