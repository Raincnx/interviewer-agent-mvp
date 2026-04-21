from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "interviewer-agent"
    env: str = "dev"

    database_url: str = "sqlite:///./app.db"

    llm_provider: str = "mock"
    llm_model: str = "mock-interviewer-v1"

    gemini_api_key: str = ""
    openai_api_key: str = ""

    max_turns: int = 5
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
