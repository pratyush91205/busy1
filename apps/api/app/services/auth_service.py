"""Authentication: turning an email and password into a token.

Route handlers stay thin; the rule about what a failed login may reveal lives
here, in one function, so there is one place to read it and one place for it to
be wrong.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.auth.passwords import spend_dummy_verification, verify_password
from app.auth.tokens import IssuedToken, issue_access_token
from app.core.config import Settings
from app.models import User
from app.repositories import user as user_repository

logger = logging.getLogger(__name__)


class InvalidCredentialsError(Exception):
    """Wrong password, or no such user. Deliberately the same exception.

    The caller turns this into one 401 with one message. An API that answers
    "no such user" for an unknown address and "wrong password" for a known one
    will happily enumerate every account it has for anyone who asks.
    """


def authenticate(db: Session, email: str, password: str) -> User:
    """Return the user matching ``email`` and ``password``.

    Raises :class:`InvalidCredentialsError` for both a missing user and a bad
    password, and spends a bcrypt verification on the missing-user path so the
    two answers also take comparable time.
    """
    user = user_repository.get_by_email(db, email)

    if user is None:
        spend_dummy_verification()
        logger.warning("Login failed for %s: no such user", email)
        raise InvalidCredentialsError

    if not verify_password(password, user.password_hash):
        logger.warning("Login failed for %s: wrong password", email)
        raise InvalidCredentialsError

    logger.info("Login succeeded for %s (user %s)", email, user.id)
    return user


def issue_token_for(user: User, settings: Settings) -> IssuedToken:
    return issue_access_token(
        user_id=user.id,
        role=user.role,
        secret=settings.jwt_secret,
        ttl_hours=settings.auth_token_ttl_hours,
    )
