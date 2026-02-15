from datetime import UTC, date, datetime, time, timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/enterprise_rag"
    REDIS_URL: str = "redis://localhost:6379/0"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_KEY: str = ""

    DAILY_TOKEN_LIMIT: int = 100000
    RESERVATION_TTL_SECONDS: int = 600

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def supabase_service_key(self) -> str:
        return self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_KEY


settings = Settings()


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_today() -> date:
    return utc_now().date()


def utc_next_reset_at(from_dt: datetime | None = None) -> datetime:
    now_utc = from_dt.astimezone(UTC) if from_dt else utc_now()
    next_day = (now_utc + timedelta(days=1)).date()
    return datetime.combine(next_day, time.min, tzinfo=UTC)
