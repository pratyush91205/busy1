"""Shared test fixtures.

The database-backed tests run against TEST_DATABASE_URL, which must be a
separate database: they migrate it down to base and back up again. When it is
not configured those tests skip with a reason rather than silently passing.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

# Importing app.main builds the application, which by design refuses to start
# without a valid configuration. Give the test process placeholder values so
# the suite does not depend on a developer's .env; the database-backed tests
# override the session dependency and use TEST_DATABASE_URL instead.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://unused:unused@localhost:5432/unused"
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, delete, insert, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import ConfigError, Settings, load_settings  # noqa: E402
from app.db.session import build_engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.deployment_check import DeploymentCheck  # noqa: E402

API_ROOT = Path(__file__).resolve().parents[1]
MISSING_ENV_FILE = API_ROOT / "tests" / "does-not-exist.env"


def build_test_settings(**overrides: object) -> Settings:
    """Settings that do not depend on a developer's .env file."""
    values: dict[str, object] = {
        "database_url": "postgresql+psycopg://unused:unused@localhost:5432/unused",
        "jwt_secret": "test-secret",
        "cors_origins": "http://localhost:3000",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


def alembic_config(url: str) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """The URL of the throwaway test database, or skip the test."""
    try:
        settings = load_settings()
    except ConfigError:
        pytest.skip(
            "No usable apps/api/.env, so TEST_DATABASE_URL could not be read. "
            "Copy .env.example to .env and point TEST_DATABASE_URL at a "
            "database that is safe to migrate up and down."
        )
    if not settings.test_database_url:
        pytest.skip(
            "TEST_DATABASE_URL is not set. Point it at a database that is safe "
            "to migrate up and down (not the deployed one)."
        )
    return settings.test_database_url


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str) -> Iterator[Engine]:
    """An engine on a test database migrated to head."""
    command.upgrade(alembic_config(test_database_url), "head")
    engine = build_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client whose database dependency is never used or overridden here."""
    with TestClient(create_app(build_test_settings())) as test_client:
        yield test_client


@pytest.fixture
def db_client(migrated_engine: Engine) -> Iterator[TestClient]:
    """A client talking to the migrated test database."""
    app = create_app(build_test_settings())

    def override_get_db() -> Iterator[Session]:
        with Session(migrated_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def empty_deployment_check(migrated_engine: Engine) -> Iterator[None]:
    """Remove the seeded rows for one test, then put them back."""
    with Session(migrated_engine) as session:
        saved = [
            {"label": row.label, "checked_at": row.checked_at}
            for row in session.execute(select(DeploymentCheck)).scalars()
        ]
        session.execute(delete(DeploymentCheck))
        session.commit()
    try:
        yield
    finally:
        with Session(migrated_engine) as session:
            if saved:
                session.execute(insert(DeploymentCheck), saved)
            session.commit()
