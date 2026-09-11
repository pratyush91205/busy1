"""Password hashing.

bcrypt directly rather than through passlib, whose bcrypt backend has been a
recurring source of version breakage, and which adds an abstraction over the
one algorithm this project uses.

bcrypt refuses a password longer than 72 bytes rather than silently ignoring
the tail. The two functions here answer that differently on purpose:

* ``hash_password`` raises. Its input comes from an operator running the seed
  script, who should be told the password is unusable rather than handed one
  that was quietly shortened.
* ``verify_password`` returns False. Its input is whatever an anonymous client
  posted, and a login attempt must never become a 500.
"""

from __future__ import annotations

import bcrypt

MAX_PASSWORD_BYTES = 72

_DUMMY_PASSWORD = b"dummy-password-for-constant-time-login"

# The unknown-email path still has to spend a bcrypt verification, or its reply
# arrives measurably sooner than a wrong-password reply and the pair becomes an
# oracle for which addresses exist. Built once at import, not per request.
_DUMMY_HASH = bcrypt.hashpw(_DUMMY_PASSWORD, bcrypt.gensalt())


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds what bcrypt will hash."""


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash of ``password``.

    Two calls with the same password return different hashes; the salt is part
    of the stored value.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"Password is {len(encoded)} bytes; bcrypt accepts at most "
            f"{MAX_PASSWORD_BYTES}."
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Whether ``password`` produced ``password_hash``. Never raises."""
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # A stored value that is not a bcrypt hash at all. That row is broken,
        # but the request is not: answer it as a failed login.
        return False


def spend_dummy_verification() -> None:
    """Spend one bcrypt verification without having a user to verify against."""
    bcrypt.checkpw(_DUMMY_PASSWORD, _DUMMY_HASH)
