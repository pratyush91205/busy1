"""Dismissal of an overdue alert, scoped to one service cycle.

There is no table of alert rows. An overdue alert is derived from the service
record (status Due, due_since older than the grace period), so the current
state is always computable from persisted data and the clock, with no
background job as its source of truth. This table records only the act of
dismissing one.

Because one service record is one service cycle, a dismissal cannot leak into
the next cycle: the next cycle is a different row, with no dismissal against
it, so the alert reappears.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin


class OverdueAlertDismissal(IdMixin, Base):
    __tablename__ = "overdue_alert_dismissals"

    service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "service_records.id",
            ondelete="RESTRICT",
            name="fk_overdue_alert_dismissals_service_id",
        ),
        nullable=False,
        unique=True,
    )
    dismissed_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_overdue_alert_dismissals_dismissed_by"),
        nullable=False,
    )
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
