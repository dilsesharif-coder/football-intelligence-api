from datetime import datetime, timezone
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "football-intelligence-api"
    app_env: str = "development"
    debug: bool = False

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/football_intelligence"
    redis_url: str = "redis://localhost:6379/0"

    api_football_key: str | None = Field(default=None, alias="API_FOOTBALL_KEY")
    odds_api_key: str | None = Field(default=None, alias="ODDS_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        env_prefix="",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
