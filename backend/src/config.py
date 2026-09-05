"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    HUNAR_API_KEY: str = ""
    HUNAR_BASE_URL: str = "https://api.voice.hunar.ai/external/v1"
    APOLLO_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./hunar.db"
    HUNAR_WEBHOOK_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    HUNAR_WEBHOOK_URL: str = ""
    APP_NAME: str = "Hunar Voice Agents API"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
