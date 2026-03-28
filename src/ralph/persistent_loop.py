"""Persistent RALPH Loop - extends RALPHLoop with DB persistence and convergence detection."""

import uuid
from datetime import datetime

from openai import AsyncOpenAI
from rich.console import Console

from src.evaluation.aggregator import Aggregator
from src.evaluation.schema import EvaluationResult
from src.personas.schema import Persona
from src.ralph.loop import RALPHLoop, PRODUCT_PRICE_KRW
from src.ralph.strategy import Strategy, StrategyResult
from src.storage.database import get_session, init_db
from src.storage.models import ExperimentRecord
from src.storage.repository import Repository

console = Console()

# Convergence threshold: if score changes less than 5% for N consecutive iterations
CONVERGENCE_THRESHOLD = 0.05
CONVERGENCE_PATIENCE = 2


class PersistentRALPHLoop(RALPHLoop):
    """RALPHLoop with DB persistence and convergence detection.

    After each iteration, saves strategy and evaluations to the database.
    Detects convergence: if avg_weighted_score change < 5% for 2 consecutive
    iterations, injects exploration or stops early.
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        database_url: str = "sqlite:///data/db/nudge.db",
        experiment_id: str | None = None,
        enable_convergence_detection: bool = True,
        stop_on_convergence: bool = False,
        **kwargs,
    ):
        super().__init__(client=client, **kwargs)
        self.database_url = database_url
        self.experiment_id = experiment_id or f"exp-{uuid.uuid4().hex[:8]}"
        self.enable_convergence_detection = enable_convergence_detection
        self.stop_on_convergence = stop_on_convergence

        # Initialize DB
        self._engine = init_db(database_url)
        self._repo = Repository(get_session(self._engine))

        # Convergence tracking
        self._consecutive_small_changes = 0

    def _save_experiment_start(self, n_iterations: int) -> None:
        """Save experiment metadata when the loop starts."""
        import json

        config = {
            "model_cheap": self.model_cheap,
            "model_expensive": self.model_expensive,
            "product_name": self.product_name,
            "product_description": self.product_description,
            "product_price": self.product_price,
            "max_turns": self.max_turns,
            "concurrency": self.concurrency,
        }
        record = ExperimentRecord(
            experiment_id=self.experiment_id,
            product_name=self.product_name,
            total_iterations=n_iterations,
            config_snapshot=json.dumps(config, ensure_ascii=False),
        )
        self._repo.save_experiment(record)

    def _save_iteration_results(
        self,
        strategy: Strategy,
        evaluations: list[EvaluationResult],
        avg_score: float,
        iteration: int,
        learnings: list[str],
    ) -> None:
        """Save strategy, evaluations, and learnings from one iteration."""
        # Save strategy
        self._repo.save_strategy(strategy, self.experiment_id, avg_score)

        # Save evaluations
        for ev in evaluations:
            self._repo.save_evaluation(ev, self.experiment_id)

        # Save learnings
        if learnings:
            self._repo.save_learnings(learnings, self.experiment_id, iteration)

    def _update_experiment_end(self) -> None:
        """Update experiment record with end timestamp."""
        from sqlmodel import select

        stmt = select(ExperimentRecord).where(
            ExperimentRecord.experiment_id == self.experiment_id
        )
        record = self._repo.session.exec(stmt).first()
        if record:
            record.ended_at = datetime.now()
            self._repo.session.add(record)
            self._repo.session.commit()

    def _check_convergence(self) -> bool:
        """Check if scores have converged (change < 5% for N consecutive iterations).

        Returns True if convergence is detected.
        """
        if not self.enable_convergence_detection:
            return False

        if len(self.result_history) < 2:
            self._consecutive_small_changes = 0
            return False

        current = self.result_history[-1].avg_weighted_score
        previous = self.result_history[-2].avg_weighted_score

        if previous == 0:
            self._consecutive_small_changes = 0
            return False

        relative_change = abs(current - previous) / abs(previous)

        if relative_change < CONVERGENCE_THRESHOLD:
            self._consecutive_small_changes += 1
            console.print(
                f"   [yellow]Convergence:[/] score change {relative_change:.1%} < {CONVERGENCE_THRESHOLD:.0%} "
                f"({self._consecutive_small_changes}/{CONVERGENCE_PATIENCE} consecutive)"
            )
        else:
            self._consecutive_small_changes = 0

        return self._consecutive_small_changes >= CONVERGENCE_PATIENCE

    def _inject_exploration(self) -> None:
        """Inject exploration by adding random contrarian learnings to break out of local optima."""
        exploration_prompts = [
            "이전 전략과 완전히 다른 접근 방식을 시도해야 합니다. 기존 패턴을 깨세요.",
            "가장 실패한 페르소나 유형에 집중하는 전략이 필요합니다.",
            "지금까지의 모든 가정을 뒤집어 보세요. 반대 전략을 테스트하세요.",
        ]
        self.all_learnings.extend(exploration_prompts)
        self._consecutive_small_changes = 0
        console.print("   [bold magenta]Exploration injected:[/] added contrarian learnings to break convergence")

    async def run(
        self,
        personas: list[Persona],
        n_iterations: int = 5,
        personas_per_iteration: int = 200,
    ) -> list[StrategyResult]:
        """Run the RALPH loop with persistence and convergence detection."""
        from src.ralph.act import execute_strategy
        from src.ralph.hypothesize import generate_hypothesis
        from src.ralph.learn import extract_learnings
        from src.ralph.plan import select_personas as plan_select_personas
        from src.ralph.reason import analyze_results

        import random

        # Save experiment metadata
        self._save_experiment_start(n_iterations)

        console.print(f"\n[bold green]Persistent RALPH Loop 시작[/] - {n_iterations}회 반복, {personas_per_iteration}명/회")
        console.print(f"  실험 ID: [cyan]{self.experiment_id}[/]")
        console.print(f"  대화 모델: [cyan]{self.model_cheap}[/]")
        console.print(f"  분석 모델: [cyan]{self.model_expensive}[/]")
        console.print(f"  DB: [cyan]{self.database_url}[/]\n")

        for iteration in range(1, n_iterations + 1):
            console.print(f"\n[bold cyan]=== Iteration {iteration}/{n_iterations} ===[/]")

            if self.on_iteration_start:
                await self.on_iteration_start(iteration, n_iterations)

            # 1. HYPOTHESIZE
            console.print("[yellow]Hypothesize:[/] 전략 생성 중...")
            strategy = await generate_hypothesis(
                client=self.client,
                model=self.model_expensive,
                iteration=iteration,
                prior_results=self.result_history,
                learnings=self.all_learnings,
            )
            self.strategy_history.append(strategy)
            console.print(f"   전략: [bold]{strategy.name}[/] - {strategy.approach}")

            # 2. PLAN
            console.print("[yellow]Plan:[/] 페르소나 선택 중...")
            focus = strategy.target_personas if strategy.target_personas else None
            selected = plan_select_personas(personas, personas_per_iteration, focus)
            console.print(f"   선택: {len(selected)}명")

            # 3. ACT
            console.print(f"[yellow]Act:[/] {len(selected)}개 대화 실행 중...")

            def on_progress(done, total):
                pass

            sessions = await execute_strategy(
                client=self.client,
                model=self.model_cheap,
                strategy=strategy,
                personas=selected,
                product_name=self.product_name,
                product_description=self.product_description,
                product_price=self.product_price,
                max_turns=self.max_turns,
                concurrency=self.concurrency,
                on_progress=on_progress,
            )

            # Aggregate conversation results
            purchase_count = sum(1 for s in sessions if s.termination_reason == "purchase")
            wishlist_count = sum(1 for s in sessions if s.termination_reason == "wishlist")
            exit_count = sum(1 for s in sessions if s.termination_reason in ("customer_exit", "max_turns"))
            purchase_rate = purchase_count / len(sessions) if sessions else 0
            total_revenue = purchase_count * PRODUCT_PRICE_KRW

            console.print(
                f"   구매: [green]{purchase_count}명[/] ({purchase_rate:.0%}) | "
                f"찜: {wishlist_count}명 | 이탈: {exit_count}명"
            )
            console.print(f"   매출: [bold]₩{total_revenue:,.0f}[/]")

            # 4. EVALUATE
            console.print("[yellow]Evaluate:[/] 대화 평가 중...")
            evaluations: list[EvaluationResult] = []
            sample_size = min(30, len(sessions))
            sample_sessions = random.sample(sessions, sample_size)

            for session in sample_sessions:
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
                model=self.model_expensive,
                sessions=sample_sessions,
                evaluations=evaluations,
            )

            # 6. LEARN
            console.print("[yellow]Learn:[/] 학습 추출 중...")
            new_learnings = await extract_learnings(
                client=self.client,
                model=self.model_expensive,
                analysis=analysis,
                prior_learnings=self.all_learnings,
            )
            self.all_learnings.extend(new_learnings)
            console.print(f"   새 학습: {len(new_learnings)}개 (누적: {len(self.all_learnings)}개)")

            # Record result
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

            # --- PERSISTENCE: save iteration results to DB ---
            try:
                self._save_iteration_results(
                    strategy=strategy,
                    evaluations=evaluations,
                    avg_score=avg_score,
                    iteration=iteration,
                    learnings=new_learnings,
                )
                console.print(f"   [dim]DB 저장 완료[/]")
            except Exception as e:
                console.print(f"   [red]DB 저장 실패: {e}[/]")

            # Save conversations (sampled ones)
            try:
                for session in sample_sessions:
                    self._repo.save_conversation(session, self.experiment_id, iteration)
            except Exception as e:
                console.print(f"   [red]대화 저장 실패: {e}[/]")

            if self.on_iteration_end:
                await self.on_iteration_end(result, strategy, analysis)

            console.print(
                f"[bold green]Iteration {iteration} 완료[/] - "
                f"점수: {avg_score:.1f}, 구매율: {purchase_rate:.0%}, 매출: ₩{total_revenue:,.0f}"
            )

            # --- CONVERGENCE DETECTION ---
            if self._check_convergence():
                if self.stop_on_convergence:
                    console.print(
                        f"\n[bold yellow]수렴 감지 - 조기 종료[/] "
                        f"(iteration {iteration}/{n_iterations})"
                    )
                    break
                else:
                    console.print(
                        f"   [bold yellow]수렴 감지 - 탐색 전략 주입[/]"
                    )
                    self._inject_exploration()

        # Update experiment end time
        try:
            self._update_experiment_end()
        except Exception as e:
            console.print(f"[red]실험 종료 기록 실패: {e}[/]")

        # Final summary
        console.print("\n[bold green]=== Persistent RALPH Loop 완료 ===[/]")
        console.print(f"실험 ID: {self.experiment_id}")
        total_revenue_all = sum(r.total_revenue for r in self.result_history)
        console.print(f"총 매출: ₩{total_revenue_all:,.0f}")
        if self.result_history:
            console.print(
                f"첫 구매율: {self.result_history[0].purchase_rate:.0%} → "
                f"최종 구매율: {self.result_history[-1].purchase_rate:.0%}"
            )

        return self.result_history
