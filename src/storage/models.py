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


# === 쿠폰 넛지 루프 결과 ===

class CouponLoopRun(SQLModel, table=True):
    """랄프 루프 실행 단위"""
    __tablename__ = "coupon_loop_runs"

    id: int | None = Field(default=None, primary_key=True)
    n_iterations: int
    personas_count: int
    baseline_revenue: float
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None


class CouponIterationResult(SQLModel, table=True):
    """루프 내 이터레이션별 결과"""
    __tablename__ = "coupon_iteration_results"

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(index=True)
    iteration: int
    strategy_id: str
    strategy_rationale: str = ""
    conditions_json: str = Field(default="", description="JSON: 25개 유형별 조건")
    coupon_users: int
    coupon_usage_rate: float
    gross_revenue: float
    discount_cost: float
    net_revenue: float
    baseline_revenue: float
    per_type_results_json: str = Field(default="", description="JSON: 유형별 결과")
    learnings_json: str = Field(default="", description="JSON: 학습 인사이트")
    analysis_json: str = Field(default="", description="JSON: 분석 결과")
    created_at: datetime = Field(default_factory=datetime.now)
