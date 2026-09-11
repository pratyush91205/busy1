"""Column mixins shared by the domain models."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, func
from sqlalchemy.orm import Mapped, mapped_column


class IdMixin:
    """A surrogate BIGINT identity primary key."""

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class CreatedAtMixin:
    """For append-only tables: they are written once and never updated."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TimestampMixin(CreatedAtMixin):
    """For mutable tables.

    updated_at is maintained by SQLAlchemy rather than a trigger, which holds
    as long as every write goes through the service layer. Sorting services by
    last update depends on it.
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
