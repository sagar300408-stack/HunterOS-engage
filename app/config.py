"""
HunterOS Engage — Application Configuration

All secrets and settings are loaded from environment variables.
Never hardcode credentials. Use .env for local development.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    # ── WhatsApp Business Cloud API ───────────────────────────────────────────
    whatsapp_access_token: str = Field(..., alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(..., alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_verify_token: str = Field(..., alias="WHATSAPP_VERIFY_TOKEN")
    whatsapp_api_version: str = Field(default="v20.0", alias="WHATSAPP_API_VERSION")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(..., alias="DATABASE_URL")

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    active_prompt_version: str = Field(default="v1", alias="ACTIVE_PROMPT_VERSION")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton. Safe to call anywhere."""
    return Settings()
