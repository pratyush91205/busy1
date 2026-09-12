"""Business rule 3: the API refuses to start without a usable DATABASE_URL.

The subprocess test is the one that matters: it proves the failure happens
while the application is being imported, not lazily on the first request.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.core.config import ConfigError, load_settings
from tests.conftest import API_ROOT, MISSING_ENV_FILE, build_test_settings


def test_load_settings_names_the_missing_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    with pytest.raises(ConfigError) as error:
        load_settings(env_file=MISSING_ENV_FILE)

    assert "DATABASE_URL" in str(error.value)


def test_importing_the_app_fails_when_database_url_is_absent() -> None:
    env = dict(os.environ)
    env.pop("DATABASE_URL", None)
    env["API_ENV_FILE"] = str(MISSING_ENV_FILE)
    env["JWT_SECRET"] = "test-secret"
    env["CORS_ORIGINS"] = "http://localhost:3000"

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ConfigError" in result.stderr
    assert "DATABASE_URL" in result.stderr


def test_a_plain_postgresql_url_is_normalised_to_psycopg() -> None:
    """Supabase, Render and psql all hand out postgresql://.

    Left alone SQLAlchemy would reach for psycopg2, which is not installed,
    and the pgbouncer connect args - keyed on the psycopg prefix - would be
    skipped. So the URL can be pasted exactly as the provider gives it.
    """
    settings = build_test_settings(
        database_url="postgresql://postgres.abc:pw@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.database_url.endswith(
        "@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"
    )


def test_an_already_psycopg_url_is_left_alone() -> None:
    url = "postgresql+psycopg://postgres:pw@localhost:5432/fleet"

    assert build_test_settings(database_url=url).database_url == url


def test_a_non_postgres_url_is_still_refused() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(database_url="mysql://root@localhost/fleet")
