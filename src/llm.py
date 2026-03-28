"""OpenRouter LLM 클라이언트 팩토리 및 공통 호출 함수"""

import asyncio

from openai import AsyncOpenAI


def create_client(api_key: str) -> AsyncOpenAI:
    """OpenRouter 호환 AsyncOpenAI 클라이언트를 생성합니다."""
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=120.0,
    )


async def chat(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict],
    max_tokens: int = 1024,
    system: str | None = None,
    retries: int = 3,
) -> str:
    """LLM 호출 공통 함수. 타임아웃 시 재시도합니다."""
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    for attempt in range(1, retries + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=full_messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == retries:
                raise
            wait = attempt * 5
            print(f"  LLM 호출 실패 (시도 {attempt}/{retries}): {e}. {wait}초 후 재시도...")
            await asyncio.sleep(wait)
