from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    model_cheap: str = Field("google/gemini-2.0-flash-001", alias="MODEL_CHEAP")
    model_expensive: str = Field("anthropic/claude-sonnet-4", alias="MODEL_EXPENSIVE")
    database_url: str = Field(
        "sqlite+aiosqlite:///data/db/nudge.db", alias="DATABASE_URL"
    )

    # Conversation defaults
    max_turns: int = 16
    conversation_timeout_sec: int = 120

    # RALPH loop defaults
    ralph_iterations: int = 5
    personas_per_iteration: int = 200
    concurrent_conversations: int = 50

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
