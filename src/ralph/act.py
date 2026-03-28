"""Act 단계: 확률 모델 기반 쿠폰 사용 판단"""

import random

from src.personas.schema import EVPersona
from src.ralph.probability_v2 import calculate_usage_probability
from src.ralph.strategy import CouponStrategy, PersonaJudgment


def execute_coupon_strategy_sync(
    strategy: CouponStrategy,
    personas: list[EVPersona],
) -> list[PersonaJudgment]:
    """확률 모델로 페르소나별 쿠폰 사용 여부를 판단합니다.

    LLM 호출 없이 실증 데이터 기반 확률 모델 + 랜덤 샘플링.
    """
    judgments = []

    for persona in personas:
        condition = strategy.get_condition(persona.type_key)

        prob, reasoning = calculate_usage_probability(
            avg_monthly_sessions=persona.avg_monthly_sessions,
            validity_days=condition.validity_days,
            discount_rate=condition.discount_rate,
            avg_charge_amount=persona.avg_charge_amount,
            age_group=persona.age_group.value,
        )

        will_use = random.random() < prob

        judgments.append(PersonaJudgment(
            persona_id=persona.id,
            type_key=persona.type_key,
            will_use_coupon=will_use,
            reasoning=reasoning,
            discount_rate=condition.discount_rate,
            validity_days=condition.validity_days,
            avg_charge_amount=persona.avg_charge_amount,
        ))

    return judgments


async def execute_coupon_strategy(
    strategy: CouponStrategy,
    personas: list[EVPersona],
    **kwargs,
) -> list[PersonaJudgment]:
    """기존 인터페이스 호환용 async wrapper."""
    return execute_coupon_strategy_sync(strategy, personas)
