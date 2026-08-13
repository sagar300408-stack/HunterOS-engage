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

    # ── Phase 2: Customer Memory ──────────────────────────────────────────────
    # Update memory summary every N messages, or immediately on significant fact
    memory_update_interval: int = Field(default=5, alias="MEMORY_UPDATE_INTERVAL")
    # Start a new conversation thread after this many hours of inactivity
    conversation_idle_hours: int = Field(default=24, alias="CONVERSATION_IDLE_HOURS")

    # ── Phase 4: Dashboard ───────────────────────────────────────────────────────
    # Secret key for signing JWT tokens. Must be at least 32 random characters.
    dashboard_secret_key: str = Field(
        default="change-me-in-production-32-chars-min",
        alias="DASHBOARD_SECRET_KEY",
    )

    # ── Phase 3.5: Orchestration ────────────────────────────────────────────────
    orchestration_max_retries: int = Field(default=3, alias="ORCHESTRATION_MAX_RETRIES")


    # Comma-separated CORS origins for the React dashboard dev server.
    # Example: "http://localhost:5173,https://dashboard.hunteros.ai"
    dashboard_cors_origins: str = Field(
        default="http://localhost:5173",
        alias="DASHBOARD_CORS_ORIGINS",
    )
    # Default workspace UUID for single-tenant bootstrapping.
    # Existing rows without workspace_id are treated as belonging to this workspace.
    default_workspace_id: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        alias="DEFAULT_WORKSPACE_ID",
    )
    enable_developer_tools: bool = Field(
        default=False,
        alias="ENABLE_DEVELOPER_TOOLS"
    )

    # ── Phase 1.3: Asynchronous Processing Pipeline ──────────────────────────
    dispatcher_poll_interval: float = Field(default=1.0, alias="DISPATCHER_POLL_INTERVAL")
    dispatcher_batch_size: int = Field(default=100, alias="DISPATCHER_BATCH_SIZE")
    dispatcher_worker_id: str = Field(default="dispatcher-1", alias="DISPATCHER_WORKER_ID")
    dispatcher_shutdown_timeout: float = Field(default=10.0, alias="DISPATCHER_SHUTDOWN_TIMEOUT")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")

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
