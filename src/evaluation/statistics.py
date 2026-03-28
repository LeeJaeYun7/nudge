"""Statistical analysis for RALPH loop results."""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, Field
from scipy.stats import chi2_contingency, ttest_ind

from src.conversation.turn import ConversationSession
from src.evaluation.schema import EvaluationResult
from src.personas.schema import Persona


# === Data Models ===


class IterationStats(BaseModel):
    """Single iteration statistics."""

    iteration: int
    avg_weighted_score: float
    purchase_rate: float
    avg_interest: float
    avg_continuation: float
    avg_emotion: float
    avg_intent: float
    avg_outcome: float
    conversation_count: int
    evaluated_count: int


class StatisticalComparison(BaseModel):
    """Statistical comparison between early and late iterations."""

    early_avg_score: float
    late_avg_score: float
    score_improvement: float
    t_statistic: float
    t_test_p_value: float
    early_purchase_rate: float
    late_purchase_rate: float
    purchase_rate_improvement: float
    chi_square_statistic: float
    chi_square_p_value: float
    is_significant: bool
    confidence_interval_95: tuple[float, float]


class PerPersonaStats(BaseModel):
    """Per-persona statistics across iterations."""

    persona_id: str
    persona_name: str
    generation: str
    reaction_pattern: str
    avg_score: float
    purchase_rate: float
    score_trend: list[float]
    conversation_count: int


class RalphAnalysis(BaseModel):
    """Complete RALPH loop analysis result."""

    iterations: list[IterationStats]
    comparison: StatisticalComparison | None = None
    per_persona: list[PerPersonaStats]
    moving_average_scores: list[float]
    convergence_detected: bool
    convergence_iteration: int | None = None


# === Functions ===


def compute_iteration_stats(
    sessions: list[ConversationSession],
    evaluations: list[EvaluationResult],
    iteration: int = 0,
) -> IterationStats:
    """Compute statistics for a single iteration."""
    conversation_count = len(sessions)
    purchase_count = sum(1 for s in sessions if s.termination_reason == "purchase")
    purchase_rate = purchase_count / conversation_count if conversation_count > 0 else 0.0

    if evaluations:
        avg_weighted = float(np.mean([e.weighted_score for e in evaluations]))
        avg_interest = float(np.mean([e.interest_level.score for e in evaluations]))
        avg_continuation = float(np.mean([e.conversation_continuation.score for e in evaluations]))
        avg_emotion = float(np.mean([e.emotional_change.score for e in evaluations]))
        avg_intent = float(np.mean([e.purchase_intent.score for e in evaluations]))
        avg_outcome = float(np.mean([e.final_outcome.score for e in evaluations]))
    else:
        avg_weighted = 0.0
        avg_interest = 0.0
        avg_continuation = 0.0
        avg_emotion = 0.0
        avg_intent = 0.0
        avg_outcome = 0.0

    return IterationStats(
        iteration=iteration,
        avg_weighted_score=round(avg_weighted, 4),
        purchase_rate=round(purchase_rate, 4),
        avg_interest=round(avg_interest, 4),
        avg_continuation=round(avg_continuation, 4),
        avg_emotion=round(avg_emotion, 4),
        avg_intent=round(avg_intent, 4),
        avg_outcome=round(avg_outcome, 4),
        conversation_count=conversation_count,
        evaluated_count=len(evaluations),
    )


def compare_early_late(
    all_iteration_stats: list[IterationStats],
    early_count: int = 2,
    late_count: int = 2,
) -> StatisticalComparison:
    """Compare early vs late iterations using t-test and chi-square."""
    if len(all_iteration_stats) < early_count + late_count:
        early_count = max(1, len(all_iteration_stats) // 2)
        late_count = max(1, len(all_iteration_stats) - early_count)

    early_stats = all_iteration_stats[:early_count]
    late_stats = all_iteration_stats[-late_count:]

    # Score comparison
    early_scores = [s.avg_weighted_score for s in early_stats]
    late_scores = [s.avg_weighted_score for s in late_stats]
    early_avg = float(np.mean(early_scores))
    late_avg = float(np.mean(late_scores))
    score_improvement = late_avg - early_avg

    # t-test (handle edge case with identical or single-element arrays)
    if len(early_scores) >= 2 and len(late_scores) >= 2:
        t_stat, t_p = ttest_ind(early_scores, late_scores, equal_var=False)
    else:
        t_stat, t_p = 0.0, 1.0

    # Handle NaN from scipy
    if math.isnan(t_stat):
        t_stat = 0.0
    if math.isnan(t_p):
        t_p = 1.0

    # Purchase rate comparison
    early_purchase_rate = float(np.mean([s.purchase_rate for s in early_stats]))
    late_purchase_rate = float(np.mean([s.purchase_rate for s in late_stats]))
    purchase_rate_improvement = late_purchase_rate - early_purchase_rate

    # Chi-square test: build 2x2 contingency table
    early_total = sum(s.conversation_count for s in early_stats)
    late_total = sum(s.conversation_count for s in late_stats)
    early_purchases = int(round(early_purchase_rate * early_total))
    late_purchases = int(round(late_purchase_rate * late_total))
    early_no_purchase = early_total - early_purchases
    late_no_purchase = late_total - late_purchases

    contingency = np.array([
        [early_purchases, early_no_purchase],
        [late_purchases, late_no_purchase],
    ])

    # chi2_contingency requires non-zero rows/columns
    if contingency.sum() > 0 and all(contingency.sum(axis=0) > 0) and all(contingency.sum(axis=1) > 0):
        chi2, chi2_p, _, _ = chi2_contingency(contingency, correction=True)
    else:
        chi2, chi2_p = 0.0, 1.0

    if math.isnan(chi2):
        chi2 = 0.0
    if math.isnan(chi2_p):
        chi2_p = 1.0

    # Wald confidence interval for purchase rate difference
    p1 = late_purchase_rate
    p2 = early_purchase_rate
    n1 = late_total if late_total > 0 else 1
    n2 = early_total if early_total > 0 else 1
    diff = p1 - p2
    se = math.sqrt((p1 * (1 - p1)) / n1 + (p2 * (1 - p2)) / n2)
    z = 1.96  # 95% CI
    ci_lower = diff - z * se
    ci_upper = diff + z * se

    is_significant = float(t_p) < 0.05

    return StatisticalComparison(
        early_avg_score=round(early_avg, 4),
        late_avg_score=round(late_avg, 4),
        score_improvement=round(score_improvement, 4),
        t_statistic=round(float(t_stat), 4),
        t_test_p_value=round(float(t_p), 4),
        early_purchase_rate=round(early_purchase_rate, 4),
        late_purchase_rate=round(late_purchase_rate, 4),
        purchase_rate_improvement=round(purchase_rate_improvement, 4),
        chi_square_statistic=round(float(chi2), 4),
        chi_square_p_value=round(float(chi2_p), 4),
        is_significant=is_significant,
        confidence_interval_95=(round(ci_lower, 4), round(ci_upper, 4)),
    )


def compute_per_persona_stats(
    all_sessions: dict[int, list[ConversationSession]],
    all_evaluations: dict[int, list[EvaluationResult]],
    personas: list[Persona],
) -> list[PerPersonaStats]:
    """Compute per-persona statistics across all iterations.

    Args:
        all_sessions: mapping from iteration number to list of sessions
        all_evaluations: mapping from iteration number to list of evaluations
        personas: list of persona definitions
    """
    persona_map = {p.id: p for p in personas}

    # Build evaluation lookup: session_id -> EvaluationResult
    eval_lookup: dict[str, EvaluationResult] = {}
    for evals in all_evaluations.values():
        for ev in evals:
            eval_lookup[ev.session_id] = ev

    # Gather per-persona data across iterations
    persona_data: dict[str, dict] = {}
    sorted_iters = sorted(all_sessions.keys())

    for persona in personas:
        pid = persona.id
        scores_by_iter: dict[int, list[float]] = {}
        total_sessions = 0
        purchase_count = 0

        for it in sorted_iters:
            sessions = all_sessions.get(it, [])
            for s in sessions:
                if s.persona_id == pid:
                    total_sessions += 1
                    if s.termination_reason == "purchase":
                        purchase_count += 1
                    if s.session_id in eval_lookup:
                        ev = eval_lookup[s.session_id]
                        scores_by_iter.setdefault(it, []).append(ev.weighted_score)

        if total_sessions == 0:
            continue

        # Compute score trend (average per iteration)
        score_trend = []
        all_scores = []
        for it in sorted_iters:
            iter_scores = scores_by_iter.get(it, [])
            if iter_scores:
                avg = float(np.mean(iter_scores))
                score_trend.append(round(avg, 4))
                all_scores.extend(iter_scores)
            else:
                # No data for this iteration — skip in trend
                pass

        avg_score = float(np.mean(all_scores)) if all_scores else 0.0
        purchase_rate = purchase_count / total_sessions

        persona_data[pid] = PerPersonaStats(
            persona_id=pid,
            persona_name=persona.name,
            generation=persona.generation.value,
            reaction_pattern=persona.reaction_pattern.value,
            avg_score=round(avg_score, 4),
            purchase_rate=round(purchase_rate, 4),
            score_trend=score_trend,
            conversation_count=total_sessions,
        )

    return list(persona_data.values())


def _compute_moving_average(scores: list[float], window: int = 2) -> list[float]:
    """Compute moving average with given window size."""
    if len(scores) < window:
        return scores[:]
    result = []
    for i in range(len(scores)):
        start = max(0, i - window + 1)
        subset = scores[start : i + 1]
        result.append(round(float(np.mean(subset)), 4))
    return result


def _detect_convergence(
    scores: list[float], threshold: float = 0.1, patience: int = 2
) -> tuple[bool, int | None]:
    """Detect if scores have converged (changes below threshold for `patience` consecutive iterations)."""
    if len(scores) < patience + 1:
        return False, None

    streak = 0
    for i in range(1, len(scores)):
        if abs(scores[i] - scores[i - 1]) < threshold:
            streak += 1
            if streak >= patience:
                # Convergence detected at iteration i - patience + 1 (1-indexed)
                return True, i - patience + 2
        else:
            streak = 0

    return False, None


def analyze_ralph_results(
    iteration_results: list[dict],
    personas: list[Persona],
) -> RalphAnalysis:
    """Main entry point: compute full statistical analysis of RALPH loop results.

    Args:
        iteration_results: list of dicts, each containing:
            - "sessions": list[ConversationSession]
            - "evaluations": list[EvaluationResult]
            - "iteration": int
        personas: list of persona definitions
    """
    # Compute per-iteration stats
    iteration_stats_list: list[IterationStats] = []
    all_sessions: dict[int, list[ConversationSession]] = {}
    all_evaluations: dict[int, list[EvaluationResult]] = {}

    for entry in iteration_results:
        it = entry["iteration"]
        sessions = entry["sessions"]
        evaluations = entry["evaluations"]
        all_sessions[it] = sessions
        all_evaluations[it] = evaluations

        stats = compute_iteration_stats(sessions, evaluations, iteration=it)
        iteration_stats_list.append(stats)

    # Comparison (need at least 2 iterations)
    comparison = None
    if len(iteration_stats_list) >= 2:
        comparison = compare_early_late(iteration_stats_list)

    # Per-persona stats
    per_persona = compute_per_persona_stats(all_sessions, all_evaluations, personas)

    # Moving average of avg_weighted_score
    scores = [s.avg_weighted_score for s in iteration_stats_list]
    moving_avg = _compute_moving_average(scores, window=2)

    # Convergence detection
    convergence_detected, convergence_iteration = _detect_convergence(scores)

    return RalphAnalysis(
        iterations=iteration_stats_list,
        comparison=comparison,
        per_persona=per_persona,
        moving_average_scores=moving_avg,
        convergence_detected=convergence_detected,
        convergence_iteration=convergence_iteration,
    )
