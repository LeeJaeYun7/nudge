import json

import anthropic

from src.ralph.strategy import Strategy, StrategyResult


async def generate_hypothesis(
    client: anthropic.AsyncAnthropic,
    model: str,
    iteration: int,
    prior_results: list[StrategyResult] | None = None,
    learnings: list[str] | None = None,
) -> Strategy:
    """과거 학습을 기반으로 새로운 영업 전략 가설을 생성합니다."""

    context = ""
    if prior_results:
        context += "\n## 이전 전략 결과\n"
        for r in prior_results[-5:]:
            context += f"- 전략 {r.strategy_id}: 평균 {r.avg_weighted_score}점, "
            context += f"구매율: {r.purchase_rate:.0%}, 매출: ₩{r.total_revenue:,.0f}, "
            context += f"인사이트: {r.key_insights}\n"

    if learnings:
        context += "\n## 축적된 학습 내용\n"
        for l in learnings[-10:]:
            context += f"- {l}\n"

    prompt = f"""당신은 온라인 쇼핑몰 세일즈 전략 설계 전문가입니다.
다양한 고객 페르소나에게 효과적으로 제품을 판매하기 위한 AI 채팅 상담원의 새로운 전략 가설을 생성하세요.

이번은 {iteration}번째 반복입니다.
{context}

## 배경
- 온라인 쇼핑몰 상품 페이지의 AI 채팅 상담원
- 고객이 상품 페이지에 접속하여 채팅으로 상담
- 무기: 리뷰/후기, 쿠폰, 무료배송, 카드할인, 즉시배송 등

## 요구사항
- 이전 결과를 분석하고, 더 효과적일 수 있는 새로운 접근을 시도하세요.
- 구체적이고 실행 가능한 전략을 설계하세요.
- 기존에 효과가 낮았던 부분을 개선하세요.

## 응답 형식 (JSON만 출력)
{{
  "name": "전략명",
  "approach": "전반적 접근 방식 설명",
  "opening_style": "첫 인사/오프닝 스타일",
  "persuasion_tactics": ["기법1", "기법2", "기법3"],
  "objection_handling": "고객 반론 시 대응 방식",
  "target_personas": ["효과적일 페르소나 유형"]
}}
"""

    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    data = json.loads(raw)

    return Strategy(
        id=f"S{iteration:03d}",
        iteration=iteration,
        **data,
    )
