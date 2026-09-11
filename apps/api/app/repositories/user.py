"""Database access for users."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def get_by_email(db: Session, email: str) -> User | None:
    """Find a user by email, case-insensitively.

    Addresses are compared folded because a manager who registered
    ``Sam@fleet.example`` and types ``sam@fleet.example`` has not got the wrong
    account, they have got the shift key. The column itself keeps whatever was
    stored.
    """
    return db.scalars(
        select(User).where(func.lower(User.email) == email.strip().lower())
    ).first()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
