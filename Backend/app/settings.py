from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    app_env: Literal["development", "test", "production"] = "development"
    port: int = Field(default=8080, ge=1, le=65535)
    public_app_origin: str = "http://localhost:3000"
    database_url: SecretStr | None = None
    db_pool_size: int = Field(default=3, ge=1, le=20)
    db_max_overflow: int = Field(default=2, ge=0, le=10)
    evidence_bucket: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_api_key: SecretStr | None = None
    ai_timeout_seconds: int = Field(default=20, gt=0)
    hold_ttl_seconds: int = Field(default=900, gt=0)
    draft_ttl_seconds: int = Field(default=1800, gt=0)
    assessment_ttl_seconds: int = Field(default=300, gt=0)
    ai_sandbox_hourly_limit: int = Field(default=20, gt=0)
    group_sandbox_hourly_limit: int = Field(default=5, gt=0)
    ai_daily_global_limit: int = Field(default=300, gt=0)

    @field_validator("public_app_origin")
    @classmethod
    def require_exact_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or "*" in parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or any(character.isspace() for character in value)
        ):
            raise ValueError("PUBLIC_APP_ORIGIN must be one exact HTTP or HTTPS origin")
        _ = parsed.port  # Validate the optional port before accepting the origin.
        return value.rstrip("/")

    @field_validator("database_url")
    @classmethod
    def require_postgresql_driver(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            try:
                driver = make_url(value.get_secret_value()).drivername
            except ArgumentError:
                raise ValueError("DATABASE_URL must be a valid PostgreSQL connection URL") from None
            if driver != "postgresql+psycopg":
                raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
        return value
