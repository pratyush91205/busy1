"""Access token signing and verification.

PyJWT rather than python-jose: maintained, and narrower than a library that
also implements JWE and JWK for algorithms this project does not use.

The token carries ``sub``, ``role`` and ``exp``. ``role`` is for logging and
for the frontend deciding which buttons to draw - never for an authorization
decision. Every such decision re-reads the user row, so a role edited in the
database takes effect on the next request rather than at the next login, and a
client that rewrites its own ``role`` claim gains nothing.

There is no refresh token. When the token expires the user signs in again.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    """Raised for a token that is malformed, expired or wrongly signed.

    Callers turn this into a single 401. The distinction between the causes is
    logged and never returned: telling a client that its signature was wrong
    rather than its token expired only helps it forge a better one.
    """


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    role: str
    expires_at: datetime


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_at: datetime


def issue_access_token(
    user_id: int, role: str, secret: str, ttl_hours: int
) -> IssuedToken:
    """Sign a token for ``user_id`` that expires ``ttl_hours`` from now."""
    expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
    payload = {
        # JWT registered claims are strings; PyJWT enforces it for "sub".
        "sub": str(user_id),
        "role": role,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return IssuedToken(jwt.encode(payload, secret, algorithm=ALGORITHM), expires_at)


def decode_access_token(token: str, secret: str) -> TokenClaims:
    """Verify ``token`` and return its claims, or raise InvalidTokenError.

    ``algorithms`` is pinned to one value. Accepting the token's own ``alg`` is
    the classic JWT forgery: a client sends ``alg: none`` and signs nothing.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError(f"sub is not a user id: {payload.get('sub')!r}") from exc

    return TokenClaims(
        user_id=user_id,
        role=str(payload.get("role", "")),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
