"""확률 모델 기반 쿠폰 사용 판단 — 버전 관리

각 버전은 독립적인 파라미터와 계산 로직을 가집니다.
새 버전을 추가하려면 ModelConfig를 만들고 MODELS에 등록하세요.
"""

import math
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """확률 모델 파라미터 설정"""
    version: str
    description: str

    # 할인 효과
    discount_threshold_pct: float = 10       # 행동 변화 최소 임계값 (%)
    elasticity_per_pct: float = 0.012        # 임계값 이상 1%p당 확률 증가
    base_effect_at_threshold: float = 0.15   # 임계값 도달 시 기본 효과
    max_discount_effect: float = 0.40        # 할인 효과 상한

    # 타이밍-할인 상호작용
    high_natural_damper: float = 0.35        # 자연방문 ≥80% 일 때 감쇠
    mid_natural_base: float = 0.5            # 자연방문 30~80% 구간 기본
    mid_natural_slope: float = 0.4           # 자연방문 30~80% 구간 기울기
    low_natural_mult: float = 2.5            # 자연방문 <30% 일 때 배수

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
        (2, 1.15),    # ≤2일 긴급
        (7, 1.05),    # ≤7일 골든타임
        (14, 1.0),    # ≤14일 보통
        (999, 0.85),  # >14일 망각
    ])

    # 최종 확률 범위
    prob_min: float = 0.01
    prob_max: float = 0.85


# ── 버전별 모델 정의 ──

V1 = ModelConfig(
    version="v1",
    description="초기 모델 — 실증 논문 기반 근사치, 경험적 추정 계수",
)

# 새 버전 예시 (파라미터만 바꾸면 됨):
# V2 = ModelConfig(
#     version="v2",
#     description="A/B 테스트 데이터 반영 — 임계값 조정",
#     discount_threshold_pct=8,
#     elasticity_per_pct=0.015,
#     high_natural_damper=0.25,
# )

# ── 모델 레지스트리 ──
MODELS: dict[str, ModelConfig] = {
    "v1": V1,
}

CURRENT_VERSION = "v1"


def get_model(version: str | None = None) -> ModelConfig:
    """버전으로 모델 설정을 가져옵니다."""
    v = version or CURRENT_VERSION
    if v not in MODELS:
        raise ValueError(f"Unknown model version: {v}. Available: {list(MODELS.keys())}")
    return MODELS[v]


def calculate_usage_probability(
    avg_monthly_sessions: float,
    validity_days: int,
    discount_rate: float,
    avg_charge_amount: float,
    age_group: str,
    version: str | None = None,
) -> tuple[float, str]:
    """쿠폰으로 인한 추가 충전 확률을 계산합니다.

    Args:
        version: 모델 버전 (None이면 CURRENT_VERSION 사용)

    Returns:
        (probability, reasoning) 튜플
    """
    m = get_model(version)
    reasons = [f"[{m.version}]"]

    # 평균 충전 간격 (일)
    avg_interval = 30 / avg_monthly_sessions if avg_monthly_sessions > 0 else 60

    # ── 1. 자연 방문 확률 (Poisson) ──
    lam = validity_days / avg_interval
    p_natural = 1 - math.exp(-lam)
    reasons.append(
        f"충전간격 {avg_interval:.0f}일/유효 {validity_days}일 → 자연방문 {p_natural:.0%}"
    )

    # ── 2. 할인 효과 (실증 탄성계수 기반) ──
    discount_pct = discount_rate * 100
    if discount_pct < m.discount_threshold_pct:
        discount_effect = discount_pct / m.discount_threshold_pct * m.base_effect_at_threshold
        reasons.append(f"할인 {discount_pct:.0f}% < 임계값 {m.discount_threshold_pct}%")
    else:
        discount_effect = (
            m.base_effect_at_threshold
            + (discount_pct - m.discount_threshold_pct) * m.elasticity_per_pct
        )
        reasons.append(f"할인 {discount_pct:.0f}% → 효과 {discount_effect:.2f}")
    discount_effect = min(discount_effect, m.max_discount_effect)

    # ── 3. 타이밍-할인 상호작용 ──
    if p_natural >= 0.8:
        p_additional = discount_effect * m.high_natural_damper
        reasons.append("자연방문↑ → 추가충전 동기↓")
    elif p_natural >= 0.3:
        p_additional = discount_effect * (m.mid_natural_base + p_natural * m.mid_natural_slope)
        reasons.append("유효기간 적절 → 할인이 트리거")
    else:
        p_additional = discount_effect * p_natural * m.low_natural_mult
        reasons.append("자연방문↓ → 강한 할인 필요")

    # ── 4. 절대 할인 금액 ──
    discount_amount = avg_charge_amount * discount_rate
    amount_mult = m.amount_tiers[-1][1]  # default
    for threshold, mult in m.amount_tiers:
        if discount_amount >= threshold:
            amount_mult = mult
            break
    reasons.append(f"할인금액 ₩{discount_amount:,.0f} → ×{amount_mult}")

    # ── 5. 연령대 디지털 리터러시 ──
    age_mult = m.age_multipliers.get(age_group, 1.0)
    reasons.append(f"{age_group} → ×{age_mult}")

    # ── 6. 유효기간 긴급성 ──
    urgency_mult = 1.0
    for max_days, mult in m.urgency_tiers:
        if validity_days <= max_days:
            urgency_mult = mult
            break
    if urgency_mult != 1.0:
        reasons.append(f"유효 {validity_days}일 → ×{urgency_mult}")

    # ── 최종 확률 ──
    final_prob = p_additional * amount_mult * age_mult * urgency_mult
    final_prob = max(m.prob_min, min(m.prob_max, final_prob))

    reasoning = " | ".join(reasons) + f" → 최종 {final_prob:.1%}"
    return final_prob, reasoning
