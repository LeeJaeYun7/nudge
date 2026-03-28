import json

from sqlmodel import Session, select

from src.conversation.turn import ConversationSession
from src.evaluation.schema import EvaluationResult
from src.ralph.strategy import Strategy
from src.storage.models import (
    ConversationRecord,
    EvaluationRecord,
    ExperimentRecord,
    LearningRecord,
    StrategyRecord,
)


class Repository:
    """데이터 저장/조회를 담당합니다."""

    def __init__(self, session: Session):
        self.session = session

    def save_experiment(self, experiment: ExperimentRecord):
        self.session.add(experiment)
        self.session.commit()

    def save_conversation(
        self,
        session: ConversationSession,
        experiment_id: str,
        iteration: int,
    ):
        record = ConversationRecord(
            session_id=session.session_id,
            experiment_id=experiment_id,
            iteration=iteration,
            strategy_id=session.strategy_id,
            persona_id=session.persona_id,
            product_name=session.product_name,
            total_turns=session.total_turns,
            termination_reason=session.termination_reason,
            transcript=session.transcript,
        )
        self.session.add(record)
        self.session.commit()

    def save_evaluation(self, ev: EvaluationResult, experiment_id: str):
        record = EvaluationRecord(
            session_id=ev.session_id,
            experiment_id=experiment_id,
            interest_level=ev.interest_level.score,
            conversation_continuation=ev.conversation_continuation.score,
            emotional_change=ev.emotional_change.score,
            purchase_intent=ev.purchase_intent.score,
            final_outcome=ev.final_outcome.score,
            weighted_score=ev.weighted_score,
            overall_summary=ev.overall_summary,
        )
        self.session.add(record)
        self.session.commit()

    def save_strategy(self, strategy: Strategy, experiment_id: str, avg_score: float = 0.0):
        record = StrategyRecord(
            strategy_id=strategy.id,
            experiment_id=experiment_id,
            iteration=strategy.iteration,
            name=strategy.name,
            approach=strategy.approach,
            opening_style=strategy.opening_style,
            persuasion_tactics=json.dumps(strategy.persuasion_tactics, ensure_ascii=False),
            objection_handling=strategy.objection_handling,
            avg_score=avg_score,
        )
        self.session.add(record)
        self.session.commit()

    def save_learnings(self, learnings: list[str], experiment_id: str, iteration: int):
        for content in learnings:
            record = LearningRecord(
                experiment_id=experiment_id,
                iteration=iteration,
                content=content,
            )
            self.session.add(record)
        self.session.commit()

    def get_evaluations_by_experiment(self, experiment_id: str) -> list[EvaluationRecord]:
        stmt = select(EvaluationRecord).where(
            EvaluationRecord.experiment_id == experiment_id
        )
        return list(self.session.exec(stmt).all())

    def get_strategies_by_experiment(self, experiment_id: str) -> list[StrategyRecord]:
        stmt = select(StrategyRecord).where(
            StrategyRecord.experiment_id == experiment_id
        )
        return list(self.session.exec(stmt).all())
