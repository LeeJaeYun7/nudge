"""단일 Sales-Customer 대화를 실행하는 디버그 스크립트"""

import asyncio

import anthropic
from rich.console import Console
from rich.panel import Panel

from src.agents.customer_agent import CustomerAgent
from src.agents.sales_agent import SalesAgent
from src.conversation.engine import ConversationEngine
from src.evaluation.evaluator import Evaluator
from src.personas.loader import load_personas

console = Console()


async def main():
    client = anthropic.AsyncAnthropic()
    model = "claude-sonnet-4-20250514"

    # 페르소나 로드 및 선택
    personas = load_personas()
    persona = personas[0]  # 첫 번째 페르소나 사용

    console.print(Panel(f"[bold]페르소나:[/] {persona.summary}", title="고객 정보"))

    # 에이전트 생성
    sales = SalesAgent(
        client=client,
        model=model,
        product_name="프리미엄 무선 이어폰",
        product_description="노이즈캔슬링, 30시간 배터리, IPX5 방수, Hi-Res 오디오 지원",
        product_price="199,000원",
    )

    customer = CustomerAgent(
        client=client,
        model=model,
        persona=persona,
    )

    # 대화 실행
    engine = ConversationEngine(max_turns=16)
    console.print("\n[bold green]대화 시작[/]\n")

    session = await engine.run(
        sales_agent=sales,
        customer_agent=customer,
        persona_id=persona.id,
        product_name="프리미엄 무선 이어폰",
    )

    # 대화 출력
    for turn in session.turns:
        if turn.speaker == "sales":
            console.print(f"[blue]🧑‍💼 판매원:[/] {turn.content}")
        else:
            console.print(f"[green]🧑 고객:[/] {turn.content}")
        console.print()

    console.print(f"[dim]종료 사유: {session.termination_reason} | 총 {session.total_turns}턴[/]\n")

    # 평가
    console.print("[bold yellow]평가 중...[/]\n")
    evaluator = Evaluator(client=client, model=model)
    result = await evaluator.evaluate(session)

    console.print(Panel(
        f"관심도: {result.interest_level.score}/10 - {result.interest_level.reasoning}\n"
        f"대화 지속도: {result.conversation_continuation.score}/10 - {result.conversation_continuation.reasoning}\n"
        f"감정 변화: {result.emotional_change.score}/10 - {result.emotional_change.reasoning}\n"
        f"구매 의향: {result.purchase_intent.score}/10 - {result.purchase_intent.reasoning}\n"
        f"최종 결과: {result.final_outcome.score}/10 - {result.final_outcome.reasoning}\n"
        f"\n[bold]종합 점수: {result.weighted_score}/10[/]\n"
        f"{result.overall_summary}",
        title="평가 결과",
    ))


if __name__ == "__main__":
    asyncio.run(main())
