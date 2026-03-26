"""OpenRouter LLM 클라이언트 팩토리 및 공통 호출 함수"""

from openai import AsyncOpenAI


def create_client(api_key: str) -> AsyncOpenAI:
    """OpenRouter 호환 AsyncOpenAI 클라이언트를 생성합니다."""
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


async def chat(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict],
    max_tokens: int = 1024,
    system: str | None = None,
) -> str:
    """LLM 호출 공통 함수. system prompt를 messages에 주입합니다."""
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=full_messages,
    )
    return response.choices[0].message.content
