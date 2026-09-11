"""Fleet vehicles and their service intervals."""

from sqlalchemy import Boolean, CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class Vehicle(IdMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("current_odometer >= 0", name="ck_vehicles_odometer_non_negative"),
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

    # Unit: days.
    service_date_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    # Unit: miles.
    service_mileage_interval: Mapped[int] = mapped_column(Integer, nullable=False)

    # Soft delete. Archived vehicles keep their service history.
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", index=True
    )
