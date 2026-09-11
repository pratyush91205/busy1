"""Service records. One record is one service cycle for one vehicle."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ServiceStatus, sql_in
from app.models.mixins import IdMixin, TimestampMixin


class ServiceRecord(IdMixin, TimestampMixin, Base):
    __tablename__ = "service_records"
    __table_args__ = (
        UniqueConstraint("vehicle_id", "cycle_number", name="uq_service_records_vehicle_cycle"),
        CheckConstraint(sql_in("status", ServiceStatus), name="ck_service_records_status"),
        CheckConstraint("cycle_number > 0", name="ck_service_records_cycle_number_positive"),
        CheckConstraint(
            "char_length(btrim(description)) > 0", name="ck_service_records_description_not_blank"
        ),
        CheckConstraint(
            "completion_odometer IS NULL OR completion_odometer >= 0",
            name="ck_service_records_completion_odometer_non_negative",
        ),
    )

    vehicle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehicles.id", ondelete="RESTRICT", name="fk_service_records_vehicle_id"),
        nullable=False,
        index=True,
    )

    # The service cycle identifier: numbered from 1 per vehicle. A new cycle is
    # a new row, which is what makes alert dismissal cycle-scoped for free.
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Set when the record is booked.
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # When this cycle first became Due. Persisted rather than recomputed so
    # that editing a vehicle's intervals cannot move an existing overdue clock.
    due_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Completion data. The odometer here starts the next cycle's mileage count.
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)
