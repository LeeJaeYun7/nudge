from datetime import datetime

from sqlmodel import Field, SQLModel


class ExperimentRecord(SQLModel, table=True):
    __tablename__ = "experiments"

    id: int | None = Field(default=None, primary_key=True)
    experiment_id: str = Field(index=True)
    product_name: str
    total_iterations: int
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None
    config_snapshot: str = Field(default="", description="JSON config")


class ConversationRecord(SQLModel, table=True):
    __tablename__ = "conversations"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    experiment_id: str = Field(index=True)
    iteration: int
    strategy_id: str
    persona_id: str
    product_name: str
    total_turns: int
    termination_reason: str
    transcript: str
    created_at: datetime = Field(default_factory=datetime.now)


class EvaluationRecord(SQLModel, table=True):
    __tablename__ = "evaluations"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    experiment_id: str = Field(index=True)
    interest_level: float
    conversation_continuation: float
    emotional_change: float
    purchase_intent: float
    final_outcome: float
    weighted_score: float
    overall_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class StrategyRecord(SQLModel, table=True):
    __tablename__ = "strategies"

    id: int | None = Field(default=None, primary_key=True)
    strategy_id: str = Field(index=True)
    experiment_id: str = Field(index=True)
    iteration: int
    name: str
    approach: str
    opening_style: str
    persuasion_tactics: str = Field(default="", description="JSON list")
    objection_handling: str = ""
    avg_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)


class LearningRecord(SQLModel, table=True):
    __tablename__ = "learnings"

    id: int | None = Field(default=None, primary_key=True)
    experiment_id: str = Field(index=True)
    iteration: int
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
