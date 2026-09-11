"""Sign-in and the current user.

There is no route that creates a user. The ten goals need sign-in, not user
management, and an open registration endpoint taking a ``role`` would hand
every client the thing the rest of the system spends its time enforcing.
Accounts come from ``scripts/create_user.py``.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.auth import LoginRequest, LoginResponse, UserPublic
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, db: DbSession, settings: AppSettings
) -> LoginResponse:
    try:
        user = auth_service.authenticate(db, payload.email, payload.password)
    except auth_service.InvalidCredentialsError:
        # One message for a wrong password and for an address that does not
        # exist. Telling them apart is an account enumeration endpoint.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    issued = auth_service.issue_token_for(user, settings)
    return LoginResponse(
        access_token=issued.access_token,
        expires_at=issued.expires_at,
        user=UserPublic.model_validate(user),
    )


@router.get("/me", response_model=UserPublic)
def read_me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)
