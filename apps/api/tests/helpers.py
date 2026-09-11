"""Fixtures' building blocks: make a user, get a token for them.

Users are inserted with raw SQL and a real bcrypt hash rather than through a
route, because there is no route that creates a user - that is the point of
spec 03, rule 8.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.auth.passwords import hash_password

PASSWORD = "correct-horse-battery-staple"


def create_user(
    engine: Engine, email: str, full_name: str, role: str, password: str = PASSWORD
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            text(
                "INSERT INTO users (email, full_name, password_hash, role) "
                "VALUES (:email, :name, :hash, :role) RETURNING id"
            ),
            {
                "email": email,
                "name": full_name,
                "hash": hash_password(password),
                "role": role,
            },
        ).scalar_one()


def auth_header(
    client: TestClient, email: str, password: str = PASSWORD
) -> dict[str, str]:
    """Log in as ``email`` and return the Authorization header for that user."""
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
