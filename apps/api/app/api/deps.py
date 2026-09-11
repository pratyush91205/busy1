"""Shared route dependencies.

``CurrentUser`` and ``require_role`` are the whole authorization mechanism for
the rest of the system. Every later phase attaches one of them rather than
writing its own check, so the Fleet Manager / Technician boundary is decided
here and nowhere else.

What they cannot express is "only the records assigned to me" - that depends on
the resource, not the role, and is filtered in the service layer that owns it.
A technician with a perfectly valid token must still be refused another
technician's record.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.tokens import InvalidTokenError, decode_access_token
from app.core.config import Settings
from app.db.session import get_db
from app.models import User
from app.repositories import user as user_repository
from app.schemas.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageParams

logger = logging.getLogger(__name__)

DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False so that a missing header reaches get_current_user and gets
# this module's wording rather than Starlette's.
bearer_scheme = HTTPBearer(auto_error=False)

NOT_AUTHENTICATED = "Not authenticated"
INVALID_TOKEN = "Invalid or expired token"


def get_app_settings(request: Request) -> Settings:
    """The settings the application was built with.

    Read off the app rather than the process-wide cache, so that a test - or a
    second app in the same process - genuinely runs on the settings it was
    given instead of whichever .env happens to be on disk.
    """
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def unauthenticated(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    """The authenticated user, or 401.

    The user row is re-read on every request. That is what makes the ``role``
    claim inside the token untrusted: a client can rewrite it, and nothing here
    consults it.
    """
    if credentials is None:
        raise unauthenticated(NOT_AUTHENTICATED)

    try:
        claims = decode_access_token(credentials.credentials, settings.jwt_secret)
    except InvalidTokenError as exc:
        # Logged, never returned. "Signature failed" rather than "expired"
        # tells a client how to forge a better token.
        logger.warning("Rejected token: %s", exc)
        raise unauthenticated(INVALID_TOKEN) from exc

    user = user_repository.get_by_id(db, claims.user_id)
    if user is None:
        # A token that outlived its user: 401, not the 500 a missing row would
        # otherwise cause further down.
        logger.warning("Token for user %s, who no longer exists", claims.user_id)
        raise unauthenticated(INVALID_TOKEN)

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str) -> Callable[..., User]:
    """A dependency that allows only ``roles`` and returns the user.

    Usage: ``user: Annotated[User, Depends(require_role("fleet_manager"))]``.
    """
    allowed = frozenset(roles)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            logger.warning(
                "User %s (%s) refused a route requiring %s",
                user.id,
                user.role,
                describe(allowed),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the {describe(allowed)} role",
            )
        return user

    return dependency


def describe(roles: Iterable[str]) -> str:
    return " or ".join(sorted(roles))


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> PageParams:
    """Page and size as query parameters, shared by every list endpoint.

    A dependency rather than a Pydantic query-parameter model: it documents
    both parameters individually in the OpenAPI schema, and the bounds are
    enforced by FastAPI before the service layer is reached.
    """
    return PageParams(page=page, limit=limit)


PageQuery = Annotated[PageParams, Depends(page_params)]
