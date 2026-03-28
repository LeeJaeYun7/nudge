"""RALPH Loop - 전기차 충전 쿠폰 최적화"""

from collections import defaultdict

from openai import AsyncOpenAI
from rich.console import Console

from src.personas.schema import EVPersona
from src.ralph.act import execute_coupon_strategy
from src.ralph.hypothesize import generate_hypothesis
from src.ralph.learn import extract_learnings
from src.ralph.reason import analyze_results
from src.ralph.strategy import (
    CouponStrategy,
    CouponStrategyResult,
    PersonaJudgment,
    TypeResult,
)

console = Console()


class RALPHLoop:
    """Hypothesize → Act → Aggregate → Reason → Learn 자가 개선 루프"""

    def __init__(
        self,
        client: AsyncOpenAI,
        model_cheap: str = "google/gemini-2.0-flash-001",
        model_expensive: str = "anthropic/claude-sonnet-4",
        baseline_revenue: float = 0.0,
        concurrency: int = 50,
    ):
        self.client = client
        self.model_cheap = model_cheap
        self.model_expensive = model_expensive
        self.baseline_revenue = baseline_revenue
        self.concurrency = concurrency

        # 상태 추적
        self.strategy_history: list[CouponStrategy] = []
        self.result_history: list[CouponStrategyResult] = []
        self.all_learnings: list[str] = []

        # 진행 콜백
        self.on_iteration_start = None
        self.on_act_progress = None
        self.on_iteration_end = None

    async def run(
        self,
        personas: list[EVPersona],
        n_iterations: int = 3,
    ) -> list[CouponStrategyResult]:
        """RALPH 루프를 n회 반복 실행합니다."""

        console.print(
            f"\n[bold green]RALPH Loop 시작[/] - {n_iterations}회 반복, {len(personas)}명"
        )
        console.print(f"  판단 모델: [cyan]{self.model_cheap}[/]")
        console.print(f"  분석 모델: [cyan]{self.model_expensive}[/]")
        console.print(f"  기준선 매출: [yellow]₩{self.baseline_revenue:,.0f}[/]\n")

        for iteration in range(1, n_iterations + 1):
            console.print(f"\n[bold cyan]=== Iteration {iteration}/{n_iterations} ===[/]")

            if self.on_iteration_start:
                await self.on_iteration_start(iteration, n_iterations)

            try:
                # 1. HYPOTHESIZE
                console.print("[yellow]Hypothesize:[/] 쿠폰 전략 생성 중...")
                console.print(f"   [dim]prior_results={len(self.result_history)}개, learnings={len(self.all_learnings)}개[/]")
                strategy = await generate_hypothesis(
                    client=self.client,
                    model=self.model_expensive,
                    iteration=iteration,
                    prior_results=self.result_history,
                    learnings=self.all_learnings,
                )
                self.strategy_history.append(strategy)
                console.print(f"   전략: [bold]{strategy.id}[/] - {strategy.rationale[:80]}")
                console.print(f"   [dim]conditions={len(strategy.conditions)}개[/]")
            except Exception as e:
                console.print(f"   [bold red]Hypothesize 에러: {e}[/]")
                import traceback; traceback.print_exc()
                continue

            try:
                # 2. ACT - 확률 모델 기반 판단
                console.print(f"[yellow]Act:[/] {len(personas)}명 확률 모델 판단 중...")
                judgments = await execute_coupon_strategy(
                    strategy=strategy,
                    personas=personas,
                )
                console.print(f"   [dim]judgments={len(judgments)}개[/]")
            except Exception as e:
                console.print(f"   [bold red]Act 에러: {e}[/]")
                import traceback; traceback.print_exc()
                continue

            # 3. AGGREGATE - 유형별 집계
            type_results = self._aggregate(judgments, strategy)
            total_coupon_users = sum(t.coupon_users for t in type_results)
            total_net = sum(t.net_revenue for t in type_results)
            usage_rate = total_coupon_users / len(personas) if personas else 0

            console.print(
                f"   쿠폰 사용: [green]{total_coupon_users}명[/] ({usage_rate:.1%}) | "
                f"순이익: [bold]₩{total_net:,.0f}[/]"
            )

            try:
                # 4. REASON
                console.print("[yellow]Reason:[/] 패턴 분석 중...")
                analysis = await analyze_results(
                    client=self.client,
                    model=self.model_expensive,
                    type_results=type_results,
                    judgments=judgments,
                )
                console.print(f"   [dim]analysis keys={list(analysis.keys()) if isinstance(analysis, dict) else 'N/A'}[/]")
            except Exception as e:
                console.print(f"   [bold red]Reason 에러: {e}[/]")
                import traceback; traceback.print_exc()
                analysis = {}

            try:
                # 5. LEARN
                console.print("[yellow]Learn:[/] 학습 추출 중...")
                new_learnings = await extract_learnings(
                    client=self.client,
                    model=self.model_expensive,
                    analysis=analysis,
                    prior_learnings=self.all_learnings,
                )
                self.all_learnings.extend(new_learnings)
                console.print(f"   새 학습: {len(new_learnings)}개 (누적: {len(self.all_learnings)}개)")
            except Exception as e:
                console.print(f"   [bold red]Learn 에러: {e}[/]")
                import traceback; traceback.print_exc()
                new_learnings = []

            # 결과 기록
            result = CouponStrategyResult(
                strategy_id=strategy.id,
                iteration=iteration,
                total_personas=len(personas),
                coupon_users=total_coupon_users,
                coupon_usage_rate=usage_rate,
                gross_revenue=sum(t.gross_revenue for t in type_results),
                discount_cost=sum(t.discount_cost for t in type_results),
                net_revenue=total_net,
                baseline_revenue=self.baseline_revenue,
                per_type_results=type_results,
                key_insights=new_learnings,
            )
            self.result_history.append(result)

            if self.on_iteration_end:
                await self.on_iteration_end(result, strategy, analysis)

            console.print(
                f"[bold green]Iteration {iteration} 완료[/] - "
                f"사용률: {usage_rate:.1%}, 순이익: ₩{total_net:,.0f}"
            )

        # 최종 요약
        console.print("\n[bold green]=== RALPH Loop 완료 ===[/]")
        console.print(f"기준선 매출: ₩{self.baseline_revenue:,.0f}")
        for r in self.result_history:
            total_with_coupon = self.baseline_revenue + r.net_revenue
            change_pct = (r.net_revenue / self.baseline_revenue * 100) if self.baseline_revenue else 0
            console.print(
                f"  {r.iteration}회차: ₩{total_with_coupon:,.0f} "
                f"(+₩{r.net_revenue:,.0f}, +{change_pct:.1f}%)"
            )

        return self.result_history

    def _aggregate(
        self,
        judgments: list[PersonaJudgment],
        strategy: CouponStrategy,
    ) -> list[TypeResult]:
        """유형별 집계 및 매출 계산"""
        groups: dict[str, list[PersonaJudgment]] = defaultdict(list)
        for j in judgments:
            groups[j.type_key].append(j)

        results = []
        for type_key, group in sorted(groups.items()):
            condition = strategy.get_condition(type_key)
            total = len(group)
            coupon_users = sum(1 for j in group if j.will_use_coupon)
            usage_rate = coupon_users / total if total else 0

            avg_charge = sum(j.avg_charge_amount for j in group) / total if total else 0
            gross = avg_charge * coupon_users
            discount_cost = avg_charge * condition.discount_rate * coupon_users
            net = gross - discount_cost

            results.append(TypeResult(
                type_key=type_key,
                total=total,
                coupon_users=coupon_users,
                usage_rate=usage_rate,
                discount_rate=condition.discount_rate,
                validity_days=condition.validity_days,
                avg_charge_amount=avg_charge,
                gross_revenue=gross,
                discount_cost=discount_cost,
                net_revenue=net,
            ))

        return results
