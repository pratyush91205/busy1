"""The immutable service timeline.

Append-only, and enforced as such by database triggers created in migration
0002 - not merely by declining to write update and delete endpoints. The
restriction holds for a Fleet Manager, for the ORM, and for a psql prompt.
"""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import AuditEventType, sql_in
from app.models.mixins import CreatedAtMixin, IdMixin


class AuditEvent(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(sql_in("event_type", AuditEventType), name="ck_audit_events_event_type"),
        # Serves both "the timeline for this service" and its chronological
        # ordering, which is the only way this table is ever read.
        Index("ix_audit_events_service_id_created_at", "service_id", "created_at"),
    )

    service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("service_records.id", ondelete="RESTRICT", name="fk_audit_events_service_id"),
        nullable=False,
    )
    # Null means the system acted, e.g. a record becoming Due on a timer.
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_audit_events_actor_id"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "metadata" is reserved by SQLAlchemy's declarative base.
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
