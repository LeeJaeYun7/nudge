"""Learn 단계: 쿠폰 최적화 학습 추출"""

import json

from openai import AsyncOpenAI

from src.llm import chat


async def extract_learnings(
    client: AsyncOpenAI,
    model: str,
    analysis: dict,
    prior_learnings: list[str] | None = None,
) -> list[str]:
    """분석 결과에서 재사용 가능한 학습 포인트를 추출합니다."""

    prior_context = ""
    if prior_learnings:
        prior_context = "\n## 기존 학습\n" + "\n".join(f"- {l}" for l in prior_learnings)

    prompt = f"""당신은 전기차 충전 쿠폰 최적화 학습 시스템입니다.
아래 분석 결과를 기반으로, 다음 전략 설계에 활용할 핵심 학습 포인트를 추출하세요.

## 이번 분석 결과
{json.dumps(analysis, ensure_ascii=False, indent=2)}
{prior_context}

## 요구사항
- 할인율/유효기간 조합에 대한 구체적 인사이트 우선
- 유형별 차별화 전략에 대한 학습
- 기존 학습과 중복되지 않는 새로운 인사이트
- 5~10개 이내

## 응답 형식 (JSON 배열)
["학습1", "학습2", ...]
"""

    raw = await chat(client, model, [{"role": "user", "content": prompt}], max_tokens=1024)
    raw = raw.strip()
    if "```" in raw:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        raw = raw[start:end]

    return json.loads(raw)
