"""Business rule 1: /health reports healthy only after touching the database."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import create_app
from tests.conftest import build_test_settings


class UnreachableSession:
    """Stands in for a session whose connection fails on first use."""

    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_reports_ok_against_a_real_database(db_client: TestClient) -> None:
    response = db_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_degraded_when_the_database_is_unreachable() -> None:
    app = create_app(build_test_settings())

    def broken_db() -> Iterator[UnreachableSession]:
        yield UnreachableSession()

    app.dependency_overrides[get_db] = broken_db

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unreachable"}
