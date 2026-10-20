from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = "dev"
    api_cors_origins: str = "http://localhost:8080"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: SecretStr
    redis_db: int = 0

    session_cookie_name: str = "jk_session"
    session_ttl_seconds: int = 28800
    login_max_failed_attempts: int = 5
    login_lockout_seconds: int = 900

    investigation_max_attempts: int = 3
    investigation_retry_backoff_seconds: int = 30
    job_lock_timeout_seconds: int = 600

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
