"""Fixtures' building blocks: make a user, get a token for them.

Users are inserted with raw SQL and a real bcrypt hash rather than through a
route, because there is no route that creates a user - that is the point of
spec 03, rule 8.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.auth.passwords import hash_password

PASSWORD = "correct-horse-battery-staple"


@lru_cache(maxsize=8)
def cached_hash(password: str) -> str:
    """Hash each distinct test password once per session.

    bcrypt is deliberately slow, which is the right property in production and
    the wrong one in a suite that seeds three users per test. Every seeded user
    shares a password, so hashing it once turns minutes into seconds. That the
    salt makes two hashes of one password differ is asserted directly in
    test_passwords.py, so nothing here depends on it.
    """
    return hash_password(password)


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
                "hash": cached_hash(password),
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
