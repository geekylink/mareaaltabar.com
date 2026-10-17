"""Application configuration loaded from environment variables / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    ENVIRONMENT: str = "development"
    DATABASE_PATH: str = str(BACKEND_DIR / "data" / "marea_alta.db")

    # Security
    SECRET_KEY: str = ""
    SESSION_TTL_HOURS: int = 8
    COOKIE_SECURE: bool = True

    # Rate limiting
    RATE_LIMIT_ATTEMPTS: int = 5
    RATE_LIMIT_WINDOW_MINUTES: int = 10

    # Logs (admin logins, menu and schedule changes)
    # How long a log row survives the daily purge, in days.
    LOG_RETENTION_DAYS: int = 90
    # The server purges expired rows itself at 07:00 at the bar. Turn off when a
    # separate process already does it — a cron calling `manage_admin.py
    # purge-logs`, for instance — so the two do not compete for the same writes.
    DAILY_LOG_PURGE: bool = True

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
