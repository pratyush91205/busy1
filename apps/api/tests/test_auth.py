"""Authentication and authorization rules (spec 03).

The role-checking tests mount ``require_role`` on a throwaway app rather than
adding a test-only route to the real one. The dependency is the thing under
test; which endpoint it happens to be attached to is not.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.api.deps import require_role
from app.auth.tokens import ALGORITHM
from app.main import create_app
from app.models import User

from .conftest import build_test_settings, client_for
from .helpers import PASSWORD, auth_header, create_user

SECRET = build_test_settings().jwt_secret
OTHER_SECRET = "a-completely-different-signing-key"

HOUR_AHEAD = datetime.now(UTC) + timedelta(hours=1)

MANAGER_EMAIL = "manager@fleet.example"
TECHNICIAN_EMAIL = "tech@fleet.example"


@pytest.fixture
def manager_id(clean_db: Engine) -> int:
    return create_user(clean_db, MANAGER_EMAIL, "Morgan Reed", "fleet_manager")


@pytest.fixture
def technician_id(clean_db: Engine) -> int:
    return create_user(clean_db, TECHNICIAN_EMAIL, "Sam Okafor", "technician")


# --- login -------------------------------------------------------------------


def test_valid_credentials_return_a_token_for_that_user(
    db_client: TestClient, manager_id: int
) -> None:
    """Rules 1 and 9."""
    response = db_client.post(
        "/auth/login", json={"email": MANAGER_EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": manager_id,
        "email": MANAGER_EMAIL,
        "full_name": "Morgan Reed",
        "role": "fleet_manager",
    }

    claims = jwt.decode(body["access_token"], SECRET, algorithms=[ALGORITHM])
    assert claims["sub"] == str(manager_id)


def test_the_login_response_never_carries_a_password_hash(
    db_client: TestClient, manager_id: int
) -> None:
    """Rule 9. Checked against the raw body, not the parsed user object."""
    response = db_client.post(
        "/auth/login", json={"email": MANAGER_EMAIL, "password": PASSWORD}
    )

    assert "password_hash" not in response.text
    assert "$2b$" not in response.text


def test_a_wrong_password_is_refused(db_client: TestClient, manager_id: int) -> None:
    """Rule 2."""
    response = db_client.post(
        "/auth/login", json={"email": MANAGER_EMAIL, "password": "not-the-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_an_unknown_email_is_refused_identically(
    db_client: TestClient, manager_id: int
) -> None:
    """Rule 2: byte-identical to a wrong password, or this is an account oracle."""
    wrong_password = db_client.post(
        "/auth/login", json={"email": MANAGER_EMAIL, "password": "not-the-password"}
    )
    unknown_email = db_client.post(
        "/auth/login", json={"email": "nobody@fleet.example", "password": PASSWORD}
    )

    assert unknown_email.status_code == wrong_password.status_code
    assert unknown_email.content == wrong_password.content


def test_login_is_case_insensitive_in_the_email(
    db_client: TestClient, manager_id: int
) -> None:
    response = db_client.post(
        "/auth/login", json={"email": MANAGER_EMAIL.upper(), "password": PASSWORD}
    )

    assert response.status_code == 200


def test_a_malformed_body_is_unprocessable_not_unauthorized(
    db_client: TestClient,
) -> None:
    response = db_client.post("/auth/login", json={"email": "not-an-email"})

    assert response.status_code == 422


# --- the current user --------------------------------------------------------


def test_me_returns_the_signed_in_users_public_fields(
    db_client: TestClient, technician_id: int
) -> None:
    response = db_client.get("/auth/me", headers=auth_header(db_client, TECHNICIAN_EMAIL))

    assert response.status_code == 200
    assert response.json() == {
        "id": technician_id,
        "email": TECHNICIAN_EMAIL,
        "full_name": "Sam Okafor",
        "role": "technician",
    }


def test_a_protected_route_without_a_header_is_unauthenticated(
    db_client: TestClient,
) -> None:
    """Rule 3."""
    response = db_client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def signed(secret: str | None, *, algorithm: str = ALGORITHM, **claims: object) -> str:
    payload: dict[str, object] = {"sub": "1", "exp": HOUR_AHEAD}
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


@pytest.mark.parametrize(
    ("label", "token"),
    [
        ("garbage", "this-is-not-a-token"),
        ("signed with another key", signed(OTHER_SECRET)),
        ("expired", signed(SECRET, exp=datetime.now(UTC) - timedelta(seconds=1))),
        ("unsigned", signed(None, algorithm="none")),
    ],
)
def test_a_bad_token_is_refused(
    db_client: TestClient, technician_id: int, label: str, token: str
) -> None:
    """Rule 4. The response says the same thing whatever the cause."""
    response = db_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401, label
    assert response.json()["detail"] == "Invalid or expired token", label


def test_a_token_for_a_deleted_user_is_unauthorized_not_an_error(
    db_client: TestClient, clean_db: Engine, technician_id: int
) -> None:
    """Rule 5."""
    headers = auth_header(db_client, TECHNICIAN_EMAIL)
    with clean_db.begin() as connection:
        connection.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": technician_id}
        )

    response = db_client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


# --- require_role ------------------------------------------------------------


def test_require_role_admits_the_named_role(
    role_client: TestClient, manager_id: int
) -> None:
    """Rule 6."""
    response = role_client.get(
        "/managers-only", headers=auth_header(role_client, MANAGER_EMAIL)
    )

    assert response.status_code == 200
    assert response.json() == {"role": "fleet_manager"}


def test_require_role_refuses_every_other_role(
    role_client: TestClient, technician_id: int
) -> None:
    """Rule 6."""
    response = role_client.get(
        "/managers-only", headers=auth_header(role_client, TECHNICIAN_EMAIL)
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This action requires the fleet_manager role"


def test_a_tampered_role_claim_buys_nothing(
    role_client: TestClient, technician_id: int
) -> None:
    """Rule 6, the important half.

    The token is validly signed - it is the application's own key - and claims
    fleet_manager. The role still comes from the database, so it is refused.
    """
    forged = jwt.encode(
        {
            "sub": str(technician_id),
            "role": "fleet_manager",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        SECRET,
        algorithm=ALGORITHM,
    )

    response = role_client.get(
        "/managers-only", headers={"Authorization": f"Bearer {forged}"}
    )

    assert response.status_code == 403


def test_require_role_without_a_token_is_unauthenticated_not_forbidden(
    role_client: TestClient,
) -> None:
    """401 and 403 answer different questions: who are you, versus may you."""
    response = role_client.get("/managers-only")

    assert response.status_code == 401


# --- no way in other than logging in -----------------------------------------


def test_the_api_exposes_no_route_that_creates_a_user(db_client: TestClient) -> None:
    """Rule 8. Roles are assigned by the seed script, never over HTTP."""
    paths = db_client.app.openapi()["paths"]  # type: ignore[attr-defined]

    assert "/auth/register" not in paths
    assert not any(
        path.rstrip("/").endswith("/users") and "post" in methods
        for path, methods in paths.items()
    )


def test_no_schema_exposes_a_password_field(db_client: TestClient) -> None:
    """Rule 9, at the contract level rather than one response at a time."""
    schemas = db_client.app.openapi()["components"]["schemas"]  # type: ignore[attr-defined]
    fields = {
        name: set(schema.get("properties", {}))
        for name, schema in schemas.items()
    }

    assert all("password_hash" not in names for names in fields.values()), fields
    # The login request is the only place a password may appear at all.
    assert {name for name, names in fields.items() if "password" in names} == {
        "LoginRequest"
    }


# --- helpers -----------------------------------------------------------------


@pytest.fixture
def role_client(clean_db: Engine) -> Iterator[TestClient]:
    """The real app plus one throwaway route guarded by require_role."""
    app = create_app(build_test_settings())

    @app.get("/managers-only")
    def managers_only(
        user: Annotated[User, Depends(require_role("fleet_manager"))],
    ) -> dict[str, str]:
        return {"role": user.role}

    with client_for(app, clean_db) as test_client:
        yield test_client
