"""Application configuration"""

import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str = "sqlite:///./data/mikrotik.db"

    # Application
    APP_NAME: str = "MikroTik Mass Updater"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API settings
    API_PREFIX: str = "/api"

    # Default credentials (can be overridden per-router)
    DEFAULT_USERNAME: Optional[str] = None
    DEFAULT_PASSWORD: Optional[str] = None

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    STATIC_DIR: Path = BASE_DIR / "backend" / "static"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # JWT Authentication
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default admin user (created on first run)
    DEFAULT_ADMIN_PASSWORD: str = "admin123"  # Change in production!

    # Scheduler
    SCHEDULER_TIMEZONE: str = "UTC"

    # Monitoring
    MONITORING_ENABLED: bool = True
    DEFAULT_PING_INTERVAL: int = 60  # seconds
    DEFAULT_HEALTH_CHECK_INTERVAL: int = 300  # seconds

    # Notifications
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_ADDRESS: Optional[str] = None

    SLACK_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # Feature flags
    FEATURE_SCHEDULING: bool = True
    FEATURE_MONITORING: bool = True
    FEATURE_NOTIFICATIONS: bool = True
    FEATURE_SCRIPTS: bool = True
    FEATURE_WEBHOOKS: bool = True
    FEATURE_REPORTS: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
