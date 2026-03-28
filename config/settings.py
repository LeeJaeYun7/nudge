from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    model_cheap: str = Field("google/gemini-2.0-flash-001", alias="MODEL_CHEAP")
    model_expensive: str = Field("anthropic/claude-sonnet-4", alias="MODEL_EXPENSIVE")
    database_url: str = Field(
        "sqlite+aiosqlite:///data/db/nudge.db", alias="DATABASE_URL"
    )

    # CSMS DB (정보계)
    csms_db_host: str = Field("192.168.50.243", alias="CSMS_DB_HOST")
    csms_db_port: int = Field(3306, alias="CSMS_DB_PORT")
    csms_db_name: str = Field("CSMS", alias="CSMS_DB_NAME")
    csms_db_user: str = Field("infoadmin", alias="CSMS_DB_USER")
    csms_db_password: str = Field("", alias="CSMS_DB_PASSWORD")

    # RALPH loop defaults
    ralph_iterations: int = 5
    personas_count: int = 2000
    concurrent_calls: int = 50

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
