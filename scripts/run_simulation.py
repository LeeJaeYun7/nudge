"""RALPH Loop 전체 시뮬레이션을 실행하는 메인 스크립트"""

import asyncio

from rich.console import Console

from config.settings import get_settings
from src.llm import create_client
from src.personas.loader import load_personas
from src.ralph.loop import RALPHLoop

console = Console()


async def main():
    settings = get_settings()
    client = create_client(settings.openrouter_api_key)

    # 페르소나 로드
    personas = load_personas()
    console.print(f"[bold]로드된 페르소나: {len(personas)}명[/]\n")

    # RALPH Loop 설정
    loop = RALPHLoop(
        client=client,
        model_cheap=settings.model_cheap,
        model_expensive=settings.model_expensive,
        product_name="프리미엄 무선 이어폰",
        product_description="노이즈캔슬링, 30시간 배터리, IPX5 방수, Hi-Res 오디오 지원",
        product_price="199,000원",
        max_turns=16,
        concurrency=3,
    )

    # 실행
    results = await loop.run(
        personas=personas,
        n_iterations=5,
        personas_per_iteration=10,
    )

    # 결과 요약
    console.print("\n[bold]═══ 최종 결과 요약 ═══[/]\n")
    for r in results:
        console.print(
            f"  Iteration {r.iteration}: "
            f"전략={r.strategy_id}, "
            f"점수={r.avg_weighted_score:.2f}, "
            f"대화={r.conversation_count}개"
        )

    console.print(f"\n  [bold green]총 학습 포인트: {len(loop.all_learnings)}개[/]")
    for i, learning in enumerate(loop.all_learnings, 1):
        console.print(f"    {i}. {learning}")


if __name__ == "__main__":
    asyncio.run(main())
