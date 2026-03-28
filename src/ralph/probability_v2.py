"""확률 모델 v2 — 타사 전환 가능성 기반

v1과의 차이:
- v1: "자주 오는 사람 = 추가 충전 동기↓" (자연방문 기반)
- v2: "저빈도 = 타사에서 전환 가능 = 추가 매출↑" (전환 잠재력 기반)

핵심 가정:
- 전기차인데 우리 충전기 이용이 적다 → 타사를 쓰고 있을 가능성 높음
- 쿠폰은 타사 → 우리 충전기로의 전환을 유도하는 도구
- 이미 우리 충전기를 많이 쓰는 사람 → 전환 여지 적음, 할인만 퍼주게 됨
"""

import math
from dataclasses import dataclass, field


@dataclass
class V2Config:
    """v2 모델 파라미터"""
    version: str = "v2"
    description: str = "타사 전환 가능성 기반 모델"

    # 할인 효과 (v1과 동일)
    discount_threshold_pct: float = 10
    elasticity_per_pct: float = 0.012
    base_effect_at_threshold: float = 0.15
    max_discount_effect: float = 0.40

    # 전환 잠재력 구간 (월 충전 횟수 → 타사 전환 가능성)
    # (최대 횟수, 전환 배수, 설명)
    switching_tiers: list = field(default_factory=lambda: [
        # 월 0~1회: 전기차인데 거의 안 옴 → 타사 비중 높음
        (1, 1.8, "타사 전환 잠재력 높음"),
        # 월 2~3회: 일부 타사 사용 가능
        (3, 1.3, "타사 전환 가능"),
        # 월 4~6회: 우리 비중 적당, 약간의 전환 여지
        (6, 1.0, "전환 여지 보통"),
        # 월 7~9회: 이미 우리 고객
        (9, 0.6, "우리 충성 고객"),
        # 월 10회+: 거의 전부 우리 충전기 → 추가 여지 매우 적음
        (999, 0.3, "추가 전환 여지 적음"),
    ])

    # 자연방문-전환 상호작용
    # 자연방문 높은데 전환 잠재력도 높은 경우 → 유효기간 내 전환 가능성 있음
    # 자연방문 낮은데 전환 잠재력 높은 경우 → 할인이 충분해야 전환
    natural_visit_weight: float = 0.3   # 자연방문 확률의 가중치 (낮을수록 전환 잠재력 중심)

    # 절대 할인 금액 구간
    amount_tiers: list = field(default_factory=lambda: [
        (10000, 1.3),
        (5000, 1.1),
        (2000, 0.9),
        (0, 0.6),
    ])

    # 연령대 디지털 리터러시
    age_multipliers: dict = field(default_factory=lambda: {
        "20대": 1.10, "30대": 1.05, "40대": 1.00, "50대": 0.75, "60대+": 0.50,
    })

    # 유효기간 긴급성
    urgency_tiers: list = field(default_factory=lambda: [
        (2, 1.15),
        (7, 1.05),
        (14, 1.0),
        (999, 0.85),
    ])

    # 최종 확률 범위
    prob_min: float = 0.01
    prob_max: float = 0.85


# 기본 설정
CONFIG = V2Config()


def calculate_usage_probability(
    avg_monthly_sessions: float,
    validity_days: int,
    discount_rate: float,
    avg_charge_amount: float,
    age_group: str,
    config: V2Config | None = None,
) -> tuple[float, str]:
    """v2: 타사 전환 가능성 기반 쿠폰 사용 확률 계산

    Returns:
        (probability, reasoning) 튜플
    """
    m = config or CONFIG
    reasons = [f"[{m.version}]"]

    avg_interval = 30 / avg_monthly_sessions if avg_monthly_sessions > 0 else 60

    # ── 1. 자연 방문 확률 (Poisson) ──
    lam = validity_days / avg_interval
    p_natural = 1 - math.exp(-lam)
    reasons.append(
        f"충전간격 {avg_interval:.0f}일/유효 {validity_days}일 -> 자연방문 {p_natural:.0%}"
    )

    # ── 2. 할인 효과 ──
    discount_pct = discount_rate * 100
    if discount_pct < m.discount_threshold_pct:
        discount_effect = discount_pct / m.discount_threshold_pct * m.base_effect_at_threshold
        reasons.append(f"할인 {discount_pct:.0f}% < 임계값")
    else:
        discount_effect = (
            m.base_effect_at_threshold
            + (discount_pct - m.discount_threshold_pct) * m.elasticity_per_pct
        )
        reasons.append(f"할인 {discount_pct:.0f}% -> 효과 {discount_effect:.2f}")
    discount_effect = min(discount_effect, m.max_discount_effect)

    # ── 3. 전환 잠재력 (v2 핵심) ──
    # 우리 충전기 이용 횟수가 적을수록 타사 전환 가능성↑
    switching_mult = m.switching_tiers[-1][1]
    switching_desc = m.switching_tiers[-1][2]
    for max_sessions, mult, desc in m.switching_tiers:
        if avg_monthly_sessions <= max_sessions:
            switching_mult = mult
            switching_desc = desc
            break
    reasons.append(f"월 {avg_monthly_sessions:.1f}회 -> x{switching_mult} ({switching_desc})")

    # ── 4. 전환-타이밍 상호작용 ──
    # 전환 잠재력이 높은 사람:
    #   - 자연방문 높으면 → 유효기간 내 전환 실현 가능성↑
    #   - 자연방문 낮으면 → 할인이 전환 트리거 역할 (할인 효과에 의존)
    # 전환 잠재력이 낮은 사람:
    #   - 어차피 우리 고객이라 추가 매출↓
    if switching_mult >= 1.3:
        # 타사 전환 잠재력 높음
        # 자연방문이 높으면 유효기간 안에 충전 기회가 있어서 전환 실현됨
        # 자연방문이 낮으면 할인에 의존 → 할인 효과가 커야 함
        trigger = discount_effect * (m.natural_visit_weight + p_natural * (1 - m.natural_visit_weight))
        reasons.append("전환 잠재력 높음 -> 할인+타이밍 복합")
    elif switching_mult >= 0.8:
        # 중간 → 기본 로직
        trigger = discount_effect * (0.4 + p_natural * 0.3)
        reasons.append("전환 여지 보통")
    else:
        # 이미 우리 고객 → 추가 매출 동기 낮음
        trigger = discount_effect * 0.2
        reasons.append("이미 충성 고객 -> 추가충전 동기 낮음")

    p_additional = trigger * switching_mult

    # ── 5. 절대 할인 금액 ──
    discount_amount = avg_charge_amount * discount_rate
    amount_mult = m.amount_tiers[-1][1]
    for threshold, mult in m.amount_tiers:
        if discount_amount >= threshold:
            amount_mult = mult
            break
    reasons.append(f"할인금액 {discount_amount:,.0f}원 -> x{amount_mult}")

    # ── 6. 연령대 디지털 리터러시 ──
    age_mult = m.age_multipliers.get(age_group, 1.0)
    reasons.append(f"{age_group} -> x{age_mult}")

    # ── 7. 유효기간 긴급성 ──
    urgency_mult = 1.0
    for max_days, mult in m.urgency_tiers:
        if validity_days <= max_days:
            urgency_mult = mult
            break
    if urgency_mult != 1.0:
        reasons.append(f"유효 {validity_days}일 -> x{urgency_mult}")

    # ── 최종 확률 ──
    final_prob = p_additional * amount_mult * age_mult * urgency_mult
    final_prob = max(m.prob_min, min(m.prob_max, final_prob))

    reasoning = " | ".join(reasons) + f" -> 최종 {final_prob:.1%}"
    return final_prob, reasoning
