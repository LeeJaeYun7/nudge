from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    model_name: str = Field("claude-haiku-4-5-20251001", alias="MODEL_NAME")
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

    # Evaluation — Haiku for cost efficiency
    eval_model: str = "claude-haiku-4-5-20251001"

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
