"""Fleet vehicles and their service intervals."""

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class Vehicle(IdMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("current_odometer >= 0", name="ck_vehicles_odometer_non_negative"),
        CheckConstraint(
            "service_baseline_odometer >= 0",
            name="ck_vehicles_baseline_odometer_non_negative",
        ),
        # A zero or negative interval would make a vehicle permanently due.
        CheckConstraint("service_date_interval > 0", name="ck_vehicles_date_interval_positive"),
        CheckConstraint(
            "service_mileage_interval > 0", name="ck_vehicles_mileage_interval_positive"
        ),
    )

    registration_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    make: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)

    # The most recently recorded reading, and the single source of truth for
    # odometer validation. There is no odometer history table; see docs.
    current_odometer: Mapped[int] = mapped_column(Integer, nullable=False)

    # Where the current service cycle counts from. Both are set when the
    # vehicle is created and again each time a service completes - the counter
    # reset the brief asks for.
    #
    # Stored rather than derived so that "is this vehicle due" is a
    # single-table predicate: no lateral join to the newest completed record on
    # every row of a fleet listing. current_odometer could not serve as its own
    # baseline anyway, since it moves.
    service_baseline_odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    service_baseline_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Unit: days.
    service_date_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    # Unit: miles.
    service_mileage_interval: Mapped[int] = mapped_column(Integer, nullable=False)

    # Soft delete. Archived vehicles keep their service history.
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", index=True
    )
