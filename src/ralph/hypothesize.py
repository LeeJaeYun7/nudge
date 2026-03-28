"""Hypothesize 단계: 쿠폰 전략 가설 생성"""

import json

from openai import AsyncOpenAI

from src.llm import chat
from src.ralph.strategy import CouponCondition, CouponStrategy, CouponStrategyResult


ALL_TYPE_KEYS = [
    f"{age}_{freq}"
    for age in ["20대", "30대", "40대", "50대", "60대+"]
    for freq in ["월1회미만", "월1~2회", "월3~4회", "월5~9회", "월10회+"]
]


async def generate_hypothesis(
    client: AsyncOpenAI,
    model: str,
    iteration: int,
    prior_results: list[CouponStrategyResult] | None = None,
    learnings: list[str] | None = None,
) -> CouponStrategy:
    """쿠폰 조건 가설을 생성합니다.

    1회차: 전체 동일 조건 (baseline)
    2회차~: 유형별 개별 최적화
    """

    if iteration == 1:
        return _generate_baseline(iteration)

    return await _generate_optimized(client, model, iteration, prior_results, learnings)


def _generate_baseline(iteration: int) -> CouponStrategy:
    """1회차: 전체 동일 조건 (할인 20%, 유효 7일)"""
    condition = CouponCondition(type_key="ALL", discount_rate=0.20, validity_days=7)
    return CouponStrategy(
        id=f"S{iteration:03d}",
        iteration=iteration,
        conditions=[condition],
        rationale="기준선 측정: 전체 동일 조건 (20% 할인, 7일 유효)",
    )


async def _generate_optimized(
    client: AsyncOpenAI,
    model: str,
    iteration: int,
    prior_results: list[CouponStrategyResult] | None,
    learnings: list[str] | None,
) -> CouponStrategy:
    """2회차~: 이전 결과 기반 유형별 최적화"""

    context = ""
    if prior_results:
        context += "\n## 이전 이터레이션 결과\n"
        for r in prior_results:
            context += f"\n### 이터레이션 {r.iteration} (순이익: ₩{r.net_revenue:,.0f})\n"
            for tr in r.per_type_results:
                context += (
                    f"- {tr.type_key}: 할인 {tr.discount_rate:.0%}/{tr.validity_days}일 → "
                    f"사용률 {tr.usage_rate:.0%}, 순이익 ₩{tr.net_revenue:,.0f}\n"
                )

    if learnings:
        context += "\n## 축적된 학습\n"
        for l in learnings:
            context += f"- {l}\n"

    prompt = f"""당신은 전기차 충전 쿠폰 최적화 전문가입니다.
이전 결과를 분석하고, 25개 유형별로 최적의 쿠폰 조건을 설계하세요.

이번은 {iteration}번째 이터레이션입니다.
{context}

## 목표
- 순이익(추가 매출 - 할인 비용)을 최대화하는 유형별 쿠폰 조건 설계
- 쿠폰이 없어도 어차피 충전할 유저에게 과도한 할인을 주지 않기
- 사용률이 낮은 유형은 조건을 매력적으로, 이미 높은 유형은 할인을 줄여 비용 절감

## 제약 조건
- 할인율: 5% ~ 30% (정수 단위)
- 유효기간: 1일 ~ 30일 (정수)

## 25개 유형 키
{json.dumps(ALL_TYPE_KEYS, ensure_ascii=False)}

## 응답 형식 (JSON만 출력)
{{
  "rationale": "전체 전략 방향 설명",
  "conditions": [
    {{"type_key": "20대_월1회미만", "discount_rate": 0.25, "validity_days": 14}},
    ...25개 전부
  ]
}}
"""

    raw = await chat(client, model, [{"role": "user", "content": prompt}], max_tokens=4096)
    raw = raw.strip()
    if "```" in raw:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        raw = raw[start:end]

    data = json.loads(raw)
    conditions = []
    for c in data["conditions"]:
        dr = c["discount_rate"]
        # LLM이 정수(18)로 반환하면 소수(0.18)로 변환
        if dr > 1:
            dr = dr / 100
        # 5%~30% 범위로 클램핑
        dr = max(0.05, min(0.30, dr))
        vd = max(1, min(30, int(c["validity_days"])))
        conditions.append(CouponCondition(
            type_key=c["type_key"],
            discount_rate=round(dr, 2),
            validity_days=vd,
        ))

    return CouponStrategy(
        id=f"S{iteration:03d}",
        iteration=iteration,
        conditions=conditions,
        rationale=data.get("rationale", ""),
    )
