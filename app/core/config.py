# =============================================================================
# DEPRECATED — Authentication Stabilization Refactor (2026-07-23)
# =============================================================================
# This is a LEGACY Settings class that duplicates app/config.py.
# It was used exclusively by app/api/deps.py (now deleted).
#
# The live configuration is in app/config.py → Settings → get_settings().
# Once confirmed no other code imports from app.core.config, this file
# is safe to delete.
# =============================================================================

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    # Core Application
    APP_NAME: str = "HunterOS Engage"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development" # development, staging, production
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_OR_IT_WILL_BE_INSECURE"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: List[AnyHttpUrl] = []

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hunteros"
    
    # Redis & Event Bus
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # AI Provider
    OPENAI_API_KEY: Optional[str] = None
    
    # Storage
    STORAGE_BACKEND: str = "local" # local, s3, etc.

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
