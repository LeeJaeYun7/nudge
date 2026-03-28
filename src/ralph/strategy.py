"""쿠폰 전략 및 결과 데이터 모델"""

from datetime import datetime
from pydantic import BaseModel, Field


class CouponCondition(BaseModel):
    """특정 유형에 적용할 쿠폰 조건"""
    type_key: str  # "30대_월3~4회"
    discount_rate: float  # 0.05 ~ 0.30
    validity_days: int  # 1 ~ 30


class CouponStrategy(BaseModel):
    """RALPH가 생성한 쿠폰 전략 (이터레이션당 1개)"""
    id: str
    iteration: int
    conditions: list[CouponCondition]  # 1회차: 1개(전체 동일), 2회차~: 25개(유형별)
    rationale: str = ""
    created_at: datetime = Field(default_factory=datetime.now)

    def get_condition(self, type_key: str) -> CouponCondition:
        """유형 키로 해당 조건을 반환합니다. 없으면 첫 번째(전체 동일) 조건을 반환."""
        for c in self.conditions:
            if c.type_key == type_key:
                return c
        return self.conditions[0]


class PersonaJudgment(BaseModel):
    """개별 페르소나의 쿠폰 사용 판단 결과"""
    persona_id: str
    type_key: str
    will_use_coupon: bool
    reasoning: str
    discount_rate: float
    validity_days: int
    avg_charge_amount: float


class TypeResult(BaseModel):
    """유형별 집계 결과"""
    type_key: str
    total: int
    coupon_users: int
    usage_rate: float
    discount_rate: float
    validity_days: int
    avg_charge_amount: float
    gross_revenue: float  # 추가 매출
    discount_cost: float  # 할인 비용
    net_revenue: float  # 순이익


class CouponStrategyResult(BaseModel):
    """이터레이션 결과"""
    strategy_id: str
    iteration: int
    total_personas: int
    coupon_users: int
    coupon_usage_rate: float
    gross_revenue: float
    discount_cost: float
    net_revenue: float
    baseline_revenue: float
    per_type_results: list[TypeResult]
    key_insights: list[str] = []
