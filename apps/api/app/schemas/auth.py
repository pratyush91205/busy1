"""Request and response shapes for authentication.

No schema here has a ``password_hash`` field, and no schema accepts a ``role``
field. Both are load-bearing: the first is why a hash cannot leak through a
response, the second is why a client cannot promote itself by posting one.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    # Only a floor and a ceiling. Enforcing composition rules on an existing
    # password would reject accounts that are already seeded.
    password: str = Field(min_length=1, max_length=200)


class UserPublic(BaseModel):
    """The only shape a user is ever serialised in."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserPublic
