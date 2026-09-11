"""Due and overdue: the two questions that are easy to conflate.

**Is a vehicle due for service?** From its intervals and the point its current
cycle counts from. A statement about a *vehicle*, and what tells a manager to
open a record.

**Is a service record overdue?** From ``status == due``, ``due_since`` and the
grace period. A statement about a *record* that was opened and then left
unbooked.

A vehicle can be due with no record open; a record can be overdue for a vehicle
that would not otherwise be due yet. Both are computed here from persisted data
and a clock that is passed in, so the current state always follows from the
database and no background job is anyone's source of truth.

``now`` is an argument rather than a ``datetime.now()`` inside these functions.
That is what lets a test age a record by two weeks without sleeping or patching
the clock, and it is why the grace period is a parameter too rather than a
module constant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from app.models import ServiceRecord, ServiceStatus, Vehicle


class DueReason(StrEnum):
    DATE = "date"
    MILEAGE = "mileage"
    BOTH = "both"


@dataclass(frozen=True)
class VehicleServiceStatus:
    """Why a vehicle is or is not due, not merely whether."""

    is_due: bool
    reason: DueReason | None
    next_due_date: date
    next_due_odometer: int
    has_open_record: bool


def vehicle_service_status(
    vehicle: Vehicle, has_open_record: bool, now: datetime
) -> VehicleServiceStatus:
    """Whether ``vehicle`` is due, and what that is measured against.

    **Either** condition makes it due - they are not required together, which
    is the part of the brief easiest to get backwards.

    Both count from ``service_baseline_*``, which is set at creation and reset
    on each completion. Counting from the vehicle's creation instead would make
    every interval permanently wrong after the first service.
    """
    next_due_date = vehicle.service_baseline_date + timedelta(
        days=vehicle.service_date_interval
    )
    next_due_odometer = (
        vehicle.service_baseline_odometer + vehicle.service_mileage_interval
    )

    # An archived vehicle is not in service, so it is never due.
    live = not vehicle.is_archived
    date_reached = live and now.date() >= next_due_date
    mileage_reached = live and vehicle.current_odometer >= next_due_odometer

    return VehicleServiceStatus(
        is_due=date_reached or mileage_reached,
        reason=describe_reason(date_reached, mileage_reached),
        next_due_date=next_due_date,
        next_due_odometer=next_due_odometer,
        has_open_record=has_open_record,
    )


def describe_reason(date_reached: bool, mileage_reached: bool) -> DueReason | None:
    if date_reached and mileage_reached:
        return DueReason.BOTH
    if date_reached:
        return DueReason.DATE
    if mileage_reached:
        return DueReason.MILEAGE
    return None


def overdue_threshold(service: ServiceRecord, grace_days: int) -> datetime | None:
    """When this record starts counting as overdue, if it ever can.

    Only a record still sitting at Due has one. Booking moves the status, so
    there is nothing to clear; completing clears ``due_since`` as well.
    """
    if service.status != ServiceStatus.DUE or service.due_since is None:
        return None
    return service.due_since + timedelta(days=grace_days)


def is_overdue(service: ServiceRecord, grace_days: int, now: datetime) -> bool:
    """Derived, never stored. Overdue is not a fifth status."""
    threshold = overdue_threshold(service, grace_days)
    return threshold is not None and now >= threshold


def utc_now() -> datetime:
    """The clock, in one place, so every caller agrees which one it is."""
    return datetime.now(UTC)
