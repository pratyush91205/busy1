"""Declarative base shared by every model."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for all ORM models; carries the metadata Alembic compares against."""
