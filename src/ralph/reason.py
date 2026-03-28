"""Reason 단계: 쿠폰 사용 결과 분석"""

import json
import random

from openai import AsyncOpenAI

from src.llm import chat
from src.ralph.strategy import PersonaJudgment, TypeResult


async def analyze_results(
    client: AsyncOpenAI,
    model: str,
    type_results: list[TypeResult],
    judgments: list[PersonaJudgment],
) -> dict:
    """유형별 쿠폰 사용 결과를 분석하여 패턴을 발견합니다."""

    # 상위/하위 유형 선별
    sorted_types = sorted(type_results, key=lambda t: t.usage_rate, reverse=True)
    top_types = sorted_types[:5]
    bottom_types = sorted_types[-5:]

    # 샘플 reasoning 수집 (사용/미사용 각 5개)
    used = [j for j in judgments if j.will_use_coupon]
    not_used = [j for j in judgments if not j.will_use_coupon]
    sample_used = random.sample(used, min(5, len(used))) if used else []
    sample_not_used = random.sample(not_used, min(5, len(not_used))) if not_used else []

    prompt = f"""당신은 전기차 충전 쿠폰 효과 분석 전문가입니다.
아래 시뮬레이션 결과를 분석하고 패턴을 발견하세요.

## 사용률 상위 5개 유형
{_format_type_results(top_types)}

## 사용률 하위 5개 유형
{_format_type_results(bottom_types)}

## 전체 통계
- 총 페르소나: {sum(t.total for t in type_results)}명
- 쿠폰 사용자: {sum(t.coupon_users for t in type_results)}명
- 전체 사용률: {sum(t.coupon_users for t in type_results) / sum(t.total for t in type_results):.1%}
- 총 순이익: ₩{sum(t.net_revenue for t in type_results):,.0f}

## 쿠폰 사용 사례 (샘플)
{chr(10).join(f'- [{j.type_key}] {j.reasoning}' for j in sample_used)}

## 쿠폰 미사용 사례 (샘플)
{chr(10).join(f'- [{j.type_key}] {j.reasoning}' for j in sample_not_used)}

## 분석 요청 (JSON 형식)
{{
  "success_patterns": ["사용률 높은 유형에서 발견된 패턴"],
  "failure_patterns": ["사용률 낮은 유형에서 발견된 패턴"],
  "persona_insights": ["유형별 인사이트"],
  "improvement_suggestions": ["다음 이터레이션 개선 제안"]
}}
"""

    raw = await chat(client, model, [{"role": "user", "content": prompt}], max_tokens=2048)
    raw = raw.strip()
    if "```" in raw:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        raw = raw[start:end]

    return json.loads(raw)


def _format_type_results(results: list[TypeResult]) -> str:
    lines = []
    for t in results:
        lines.append(
            f"- {t.type_key}: 할인 {t.discount_rate:.0%}/{t.validity_days}일 → "
            f"사용률 {t.usage_rate:.0%} ({t.coupon_users}/{t.total}명), "
            f"순이익 ₩{t.net_revenue:,.0f}"
        )
    return "\n".join(lines)
