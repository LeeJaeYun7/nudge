import anthropic
from rich.console import Console

from src.evaluation.aggregator import Aggregator
from src.evaluation.evaluator import Evaluator
from src.evaluation.schema import EvaluationResult
from src.personas.schema import Persona
from src.ralph.act import execute_strategy
from src.ralph.hypothesize import generate_hypothesis
from src.ralph.learn import extract_learnings
from src.ralph.plan import select_personas
from src.ralph.reason import analyze_results
from src.ralph.strategy import Strategy, StrategyResult

console = Console()

PRODUCT_PRICE_KRW = 199000  # 기본 판매가


class RALPHLoop:
    """Reason -> Act -> Learn -> Plan -> Hypothesize 자기 개선 루프"""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-haiku-4-5-20251001",
        product_name: str = "",
        product_description: str = "",
        product_price: str = "",
        max_turns: int = 16,
        concurrency: int = 50,
    ):
        self.client = client
        self.model = model
        self.product_name = product_name
        self.product_description = product_description
        self.product_price = product_price
        self.max_turns = max_turns
        self.concurrency = concurrency
        self.evaluator = Evaluator(client=client, model=model)

        # 상태 추적
        self.strategy_history: list[Strategy] = []
        self.result_history: list[StrategyResult] = []
        self.all_learnings: list[str] = []

        # 진행 콜백
        self.on_iteration_start = None
        self.on_conversation_progress = None
        self.on_evaluation_progress = None
        self.on_iteration_end = None

    async def run(
        self,
        personas: list[Persona],
        n_iterations: int = 5,
        personas_per_iteration: int = 200,
    ) -> list[StrategyResult]:
        """RALPH 루프를 n회 반복 실행합니다."""

        console.print(f"\n[bold green]RALPH Loop 시작[/] - {n_iterations}회 반복, {personas_per_iteration}명/회\n")

        for iteration in range(1, n_iterations + 1):
            console.print(f"\n[bold cyan]━━━ Iteration {iteration}/{n_iterations} ━━━[/]")

            if self.on_iteration_start:
                await self.on_iteration_start(iteration, n_iterations)

            # 1. HYPOTHESIZE
            console.print("[yellow]Hypothesize:[/] 전략 생성 중...")
            strategy = await generate_hypothesis(
                client=self.client,
                model=self.model,
                iteration=iteration,
                prior_results=self.result_history,
                learnings=self.all_learnings,
            )
            self.strategy_history.append(strategy)
            console.print(f"   전략: [bold]{strategy.name}[/] — {strategy.approach}")

            # 2. PLAN
            console.print("[yellow]Plan:[/] 페르소나 선택 중...")
            focus = strategy.target_personas if strategy.target_personas else None
            selected = select_personas(personas, personas_per_iteration, focus)
            console.print(f"   선택: {len(selected)}명")

            # 3. ACT — 규칙 기반 고객으로 대화 실행
            console.print(f"[yellow]Act:[/] {len(selected)}개 대화 실행 중...")

            def on_progress(done, total):
                if self.on_conversation_progress:
                    import asyncio
                    asyncio.get_event_loop().call_soon(
                        lambda: None  # SSE에서 처리
                    )

            sessions = await execute_strategy(
                client=self.client,
                model=self.model,
                strategy=strategy,
                personas=selected,
                product_name=self.product_name,
                product_description=self.product_description,
                product_price=self.product_price,
                max_turns=self.max_turns,
                concurrency=self.concurrency,
                on_progress=on_progress,
            )

            # 결과 집계
            purchase_count = sum(1 for s in sessions if s.termination_reason == "purchase")
            wishlist_count = sum(1 for s in sessions if s.termination_reason == "wishlist")
            exit_count = sum(1 for s in sessions if s.termination_reason in ("customer_exit", "max_turns"))
            purchase_rate = purchase_count / len(sessions) if sessions else 0
            total_revenue = purchase_count * PRODUCT_PRICE_KRW

            console.print(f"   구매: [green]{purchase_count}명[/] ({purchase_rate:.0%}) | "
                          f"찜: {wishlist_count}명 | 이탈: {exit_count}명")
            console.print(f"   매출: [bold]₩{total_revenue:,.0f}[/]")

            # 4. EVALUATE
            console.print("[yellow]Evaluate:[/] 대화 평가 중...")
            evaluations: list[EvaluationResult] = []
            # 비용 절감: 전체 대신 샘플 30개만 평가
            sample_size = min(30, len(sessions))
            import random
            sample_sessions = random.sample(sessions, sample_size)

            for i, session in enumerate(sample_sessions):
                try:
                    ev = await self.evaluator.evaluate(session)
                    evaluations.append(ev)
                except Exception as e:
                    console.print(f"   [red]평가 실패: {e}[/]")

            if evaluations:
                stats = Aggregator.aggregate(evaluations)
                avg_score = stats["weighted_total"]["mean"]
            else:
                avg_score = 0.0
            console.print(f"   평균 점수: [bold]{avg_score:.1f}[/] (샘플 {len(evaluations)}개)")

            # 5. REASON
            console.print("[yellow]Reason:[/] 패턴 분석 중...")
            analysis = await analyze_results(
                client=self.client,
                model=self.model,
                sessions=sample_sessions,
                evaluations=evaluations,
            )

            # 6. LEARN
            console.print("[yellow]Learn:[/] 학습 추출 중...")
            new_learnings = await extract_learnings(
                client=self.client,
                model=self.model,
                analysis=analysis,
                prior_learnings=self.all_learnings,
            )
            self.all_learnings.extend(new_learnings)
            console.print(f"   새 학습: {len(new_learnings)}개 (누적: {len(self.all_learnings)}개)")

            # 결과 기록
            result = StrategyResult(
                strategy_id=strategy.id,
                iteration=iteration,
                avg_weighted_score=avg_score,
                conversation_count=len(sessions),
                purchase_count=purchase_count,
                wishlist_count=wishlist_count,
                exit_count=exit_count,
                purchase_rate=purchase_rate,
                total_revenue=total_revenue,
                best_persona_types=analysis.get("persona_insights", [])[:3],
                worst_persona_types=[],
                key_insights=new_learnings[:3],
            )
            self.result_history.append(result)

            if self.on_iteration_end:
                await self.on_iteration_end(result, strategy)

            console.print(f"[bold green]Iteration {iteration} 완료[/] — "
                          f"점수: {avg_score:.1f}, 구매율: {purchase_rate:.0%}, 매출: ₩{total_revenue:,.0f}")

        # 최종 요약
        console.print("\n[bold green]━━━ RALPH Loop 완료 ━━━[/]")
        total_revenue_all = sum(r.total_revenue for r in self.result_history)
        console.print(f"총 매출: ₩{total_revenue_all:,.0f}")
        console.print(f"첫 구매율: {self.result_history[0].purchase_rate:.0%} → "
                      f"최종 구매율: {self.result_history[-1].purchase_rate:.0%}")

        return self.result_history
