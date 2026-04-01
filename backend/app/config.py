"""Application configuration"""

import secrets
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List


def _get_persistent_secret_key() -> str:
    """Load a stable secret key from disk or create it on first run."""
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data"
    secret_path = data_dir / ".secret_key"

    data_dir.mkdir(parents=True, exist_ok=True)

    if secret_path.exists():
        secret_key = secret_path.read_text(encoding="utf-8").strip()
        if secret_key:
            return secret_key

    secret_key = secrets.token_urlsafe(32)
    secret_path.write_text(secret_key, encoding="utf-8")
    return secret_key


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
    TRUSTED_HOSTS: List[str] = ["*"]

    # Auth rate limiting
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 300
    AUTH_RATE_LIMIT_LOGIN_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_REFRESH_ATTEMPTS: int = 10

    # JWT Authentication
    SECRET_KEY: str = _get_persistent_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None

    # Default admin user (created on first run)
    DEFAULT_ADMIN_PASSWORD: Optional[str] = None

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
