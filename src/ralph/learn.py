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
        prior_context = "\n## 기존 학습 내용\n" + "\n".join(f"- {l}" for l in prior_learnings)

    prompt = f"""당신은 온라인 쇼핑몰 세일즈 전략 학습 시스템입니다.
아래 분석 결과를 기반으로, 다음 전략 설계에 활용할 수 있는 핵심 학습 포인트를 추출하세요.

## 이번 분석 결과
{json.dumps(analysis, ensure_ascii=False, indent=2)}
{prior_context}

## 요구사항
- 구체적이고 실행 가능한 학습만 추출하세요.
- 기존 학습과 중복되지 않는 새로운 인사이트를 우선하세요.
- 기존 학습 중 반박되는 것이 있으면 업데이트 버전을 포함하세요.
- 5~10개 이내로 추출하세요.

## 응답 형식 (JSON 배열)
["학습1", "학습2", "학습3"]
"""

    raw = await chat(client, model, [{"role": "user", "content": prompt}], max_tokens=1024)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
