"""Access token signing and verification (spec 03, rules 4 and 7)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.tokens import (
    ALGORITHM,
    InvalidTokenError,
    decode_access_token,
    issue_access_token,
)

SECRET = "the-signing-key"
OTHER_SECRET = "a-different-signing-key"


def issue(user_id: int = 7, role: str = "technician", ttl_hours: int = 12):
    return issue_access_token(user_id, role, SECRET, ttl_hours)


def test_round_trip_returns_the_user_id_and_role():
    claims = decode_access_token(issue().access_token, SECRET)

    assert claims.user_id == 7
    assert claims.role == "technician"


def test_expiry_is_the_configured_ttl_from_now():
    issued = issue(ttl_hours=12)

    assert issued.expires_at - datetime.now(UTC) == pytest.approx(
        timedelta(hours=12), abs=timedelta(seconds=5)
    )


def test_garbage_is_refused():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-token", SECRET)


def test_a_token_signed_with_another_key_is_refused():
    with pytest.raises(InvalidTokenError):
        decode_access_token(issue().access_token, OTHER_SECRET)


def test_an_expired_token_is_refused():
    with pytest.raises(InvalidTokenError):
        decode_access_token(issue(ttl_hours=-1).access_token, SECRET)


def test_an_unsigned_token_is_refused():
    """`alg: none` is the classic forgery, so the algorithm is pinned."""
    forged = jwt.encode({"sub": "7", "role": "fleet_manager"}, None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_access_token(forged, SECRET)


def test_a_token_without_an_expiry_is_refused():
    forever = jwt.encode({"sub": "7", "role": "technician"}, SECRET, algorithm=ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(forever, SECRET)


def test_a_subject_that_is_not_a_user_id_is_refused():
    nonsense = jwt.encode(
        {"sub": "not-a-number", "exp": datetime.now(UTC) + timedelta(hours=1)},
        SECRET,
        algorithm=ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(nonsense, SECRET)
