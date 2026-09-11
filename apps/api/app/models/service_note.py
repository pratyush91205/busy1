"""Service notes. Append-only: no updated_at, and no update or delete path."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User
from app.models.mixins import CreatedAtMixin, IdMixin


class ServiceNote(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "service_notes"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(content)) > 0", name="ck_service_notes_content_not_blank"
        ),
    )

    service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("service_records.id", ondelete="RESTRICT", name="fk_service_notes_service_id"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_service_notes_author_id"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    author: Mapped["User"] = relationship(lazy="raise_on_sql")
