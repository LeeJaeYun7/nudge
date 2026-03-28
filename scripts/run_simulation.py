"""EV 충전 쿠폰 넛지 RALPH Loop 시뮬레이션"""

import asyncio
import os
import sys

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)
os.environ["PYTHONIOENCODING"] = "utf-8"

from rich.console import Console

from config.settings import get_settings
from src.csms.revenue import calculate_baseline_revenue
from src.llm import create_client
from src.personas.loader import generate_personas_from_db
from src.ralph.loop import RALPHLoop

console = Console()


async def main():
    settings = get_settings()
    client = create_client(settings.openrouter_api_key)

    # 기준선 매출
    console.print("[bold]기준선 매출 조회 중...[/]")
    baseline = calculate_baseline_revenue()
    baseline_monthly = float(baseline["monthly_revenue"])
    console.print(f"  월 매출: ₩{baseline_monthly:,.0f}\n")

    # 페르소나 생성
    console.print("[bold]DB에서 페르소나 생성 중...[/]")
    personas = generate_personas_from_db(settings.personas_count)
    console.print(f"  생성: {len(personas)}명\n")

    # RALPH Loop 실행
    loop = RALPHLoop(
        client=client,
        model_cheap=settings.model_cheap,
        model_expensive=settings.model_expensive,
        baseline_revenue=baseline_monthly,
        concurrency=settings.concurrent_calls,
    )

    results = await loop.run(
        personas=personas,
        n_iterations=settings.ralph_iterations,
    )

    # 최종 요약
    console.print("\n[bold]═══ 최종 결과 요약 ═══[/]\n")
    console.print(f"  기준선 매출: ₩{baseline_monthly:,.0f}")
    for r in results:
        total = baseline_monthly + r.net_revenue
        pct = r.net_revenue / baseline_monthly * 100 if baseline_monthly else 0
        console.print(
            f"  {r.iteration}회차: ₩{total:,.0f} "
            f"(+₩{r.net_revenue:,.0f}, +{pct:.1f}%) "
            f"사용률: {r.coupon_usage_rate:.1%}"
        )

    console.print(f"\n  [bold green]총 학습 포인트: {len(loop.all_learnings)}개[/]")
    for i, learning in enumerate(loop.all_learnings, 1):
        console.print(f"    {i}. {learning}")


if __name__ == "__main__":
    asyncio.run(main())
