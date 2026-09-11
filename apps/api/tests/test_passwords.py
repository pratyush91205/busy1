"""Password hashing rules (spec 03, rule 1)."""

import pytest

from app.auth.passwords import (
    MAX_PASSWORD_BYTES,
    PasswordTooLongError,
    hash_password,
    verify_password,
)

PASSWORD = "correct-horse-battery-staple"


def test_hash_verifies_against_its_own_password():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_hash_rejects_a_different_password():
    assert verify_password("not-the-password", hash_password(PASSWORD)) is False


def test_two_hashes_of_the_same_password_differ():
    """A shared salt would make identical passwords visible in the table."""
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_hash_is_not_the_password():
    assert PASSWORD not in hash_password(PASSWORD)


def test_hashing_an_overlong_password_is_refused_not_truncated():
    with pytest.raises(PasswordTooLongError):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))


def test_verifying_an_overlong_password_returns_false():
    """Client-supplied input must fail the login, never raise a 500."""
    assert verify_password("a" * (MAX_PASSWORD_BYTES + 1), hash_password(PASSWORD)) is False


def test_verifying_against_a_hash_that_is_not_bcrypt_returns_false():
    assert verify_password(PASSWORD, "not-a-bcrypt-hash") is False
