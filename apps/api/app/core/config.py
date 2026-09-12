"""Application configuration.

Settings are read from the environment (falling back to an ``.env`` file) once,
at startup. A missing or unusable value must stop the process immediately: a
service that boots with a broken ``DATABASE_URL`` and only fails on its first
request is how a broken deployment reaches production unnoticed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = API_ROOT / ".env"

PSYCOPG_PREFIX = "postgresql+psycopg://"
PLAIN_PREFIX = "postgresql://"


class ConfigError(RuntimeError):
    """Raised when the environment does not describe a usable application."""


class Settings(BaseSettings):
    """Everything the application needs from its environment."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    cors_origins: str
    overdue_grace_period_days: int = 7

    # How long an access token stays valid. There is no refresh token, so this
    # is also how long a session lasts before the user has to sign in again.
    auth_token_ttl_hours: int = 12

    # Alembic needs a session-mode connection (it uses prepared statements);
    # the application itself runs against the transaction pooler. When unset,
    # migrations fall back to database_url.
    alembic_database_url: str | None = None

    # Used by pytest only. Tests migrate this database up and down, so it must
    # never point at a deployed database.
    test_database_url: str | None = None

    @field_validator("database_url", "alembic_database_url", "test_database_url")
    @classmethod
    def check_database_url(cls, value: str | None) -> str | None:
        """Accept a plain postgresql:// URL, but store the psycopg one.

        Supabase, Render and psql all hand out ``postgresql://``. Left alone,
        SQLAlchemy reads that as "use the default driver" and reaches for
        psycopg2, which is not installed - and the pgbouncer connect args,
        which are keyed on the psycopg prefix, would be silently skipped.

        Normalising here means a URL can be pasted exactly as the provider
        gives it and still get the right driver and the pooler settings.
        """
        if not value:
            return None
        if value.startswith(PSYCOPG_PREFIX):
            return value
        if value.startswith(PLAIN_PREFIX):
            return PSYCOPG_PREFIX + value[len(PLAIN_PREFIX) :]

        scheme = value.split(":", 1)[0]
        raise ValueError(
            "must be a PostgreSQL URL beginning with postgresql:// or "
            f"postgresql+psycopg://, got scheme {scheme!r}"
        )

    @field_validator("cors_origins")
    @classmethod
    def check_cors_origins(cls, value: str) -> str:
        origins = split_origins(value)
        if not origins:
            raise ValueError("must list at least one allowed origin")
        if "*" in origins:
            raise ValueError(
                "must not contain '*'. Credentialed requests and a wildcard "
                "origin cannot be combined, so list the exact origins instead"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """The allowed browser origins, in the order they were configured."""
        return split_origins(self.cors_origins)

    @property
    def migration_database_url(self) -> str:
        """The URL Alembic should connect with."""
        return self.alembic_database_url or self.database_url


def split_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Build :class:`Settings`, turning validation failures into ConfigError.

    ``env_file`` defaults to ``apps/api/.env`` (overridable with the
    ``API_ENV_FILE`` environment variable). Pass an explicit ``env_file`` of a
    path that does not exist to read the process environment only.
    """
    if env_file is None:
        env_file = os.environ.get("API_ENV_FILE") or DEFAULT_ENV_FILE

    try:
        return Settings(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as exc:
        raise ConfigError(describe_config_failure(exc, env_file)) from exc


def describe_config_failure(exc: ValidationError, env_file: str | Path) -> str:
    problems = "; ".join(
        f"{str(error['loc'][0]).upper()}: {error['msg']}" for error in exc.errors()
    )
    return (
        "The application cannot start because its configuration is invalid. "
        f"{problems}. Set these variables in {env_file} or in the deployment "
        "environment (see apps/api/.env.example)."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The process-wide settings, loaded once."""
    return load_settings()
