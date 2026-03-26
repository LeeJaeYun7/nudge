from statistics import mean, stdev

from src.evaluation.schema import EvaluationResult


class Aggregator:
    """여러 대화의 평가 결과를 집계합니다."""

    @staticmethod
    def aggregate(results: list[EvaluationResult]) -> dict:
        """평가 결과 리스트의 통계를 계산합니다."""
        if not results:
            return {}

        dimensions = [
            "interest_level",
            "conversation_continuation",
            "emotional_change",
            "purchase_intent",
            "final_outcome",
        ]

        stats: dict = {}
        for dim in dimensions:
            scores = [getattr(r, dim).score for r in results]
            stats[dim] = {
                "mean": round(mean(scores), 2),
                "stdev": round(stdev(scores), 2) if len(scores) > 1 else 0.0,
                "min": min(scores),
                "max": max(scores),
            }

        weighted_scores = [r.weighted_score for r in results]
        stats["weighted_total"] = {
            "mean": round(mean(weighted_scores), 2),
            "stdev": round(stdev(weighted_scores), 2) if len(weighted_scores) > 1 else 0.0,
            "min": min(weighted_scores),
            "max": max(weighted_scores),
        }

        stats["count"] = len(results)
        return stats
