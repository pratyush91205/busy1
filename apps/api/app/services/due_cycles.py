"""Opening a service cycle when a vehicle falls due.

A vehicle reaching its date or mileage interval is a fact about the vehicle. A
Due service record is what everything downstream acts on: the overdue clock,
the alert, the dashboard, the list a manager books from. Without this module
the first only became the second when a manager noticed and opened a record by
hand - so a vehicle nobody was watching was never overdue and never alerted,
which is exactly the vehicle an alert exists for.

There is no background job. A vehicle can fall due in two ways, and each is
handled where it happens:

* **Mileage** only moves when something writes an odometer reading - a vehicle
  edit or a bulk upload row. Those call ``open_cycle_if_due`` inside their own
  transaction, so ``due_since`` is the moment the reading crossed.
* **Date** moves with the clock, and nothing writes when a date passes. So the
  read paths that depend on it call ``open_due_cycles`` first. It is
  idempotent - it only opens a cycle for a vehicle with none open - and it
  backdates ``due_since`` to the day the interval landed, so *when* the sweep
  happens to run does not change when the overdue clock started.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditEventType, ServiceRecord, ServiceStatus, Vehicle
from app.repositories import audit as audit_repository
from app.repositories import service as service_repository
from app.repositories.vehicle import due_predicate
from app.services import maintenance

logger = logging.getLogger(__name__)

DESCRIPTIONS = {
    maintenance.DueReason.DATE: "Scheduled service - date interval reached",
    maintenance.DueReason.MILEAGE: "Scheduled service - mileage interval reached",
    maintenance.DueReason.BOTH: (
        "Scheduled service - date and mileage intervals reached"
    ),
}


def open_cycle_if_due(
    db: Session, vehicle: Vehicle, now: datetime
) -> ServiceRecord | None:
    """Open the next cycle for ``vehicle`` if it is due and has none open.

    Adds to the session without committing: the change that made the vehicle
    due - a reading that crossed the interval - and the record it caused commit
    together, or neither does.
    """
    if service_repository.get_open_for_vehicle(db, vehicle.id) is not None:
        return None

    status = maintenance.vehicle_service_status(
        vehicle, has_open_record=False, now=now
    )
    if not status.is_due or status.reason is None:
        return None

    service = ServiceRecord(
        vehicle_id=vehicle.id,
        cycle_number=service_repository.next_cycle_number(db, vehicle.id),
        description=DESCRIPTIONS[status.reason],
        status=ServiceStatus.DUE,
        due_since=due_moment(status, now),
    )
    db.add(service)
    # For the audit event's service_id; still inside the caller's transaction.
    db.flush()

    audit_repository.record(
        db,
        service_id=service.id,
        # Nobody opened it: the vehicle fell due. Null actor is the timeline's
        # existing way of saying the system acted.
        actor_id=None,
        event_type=AuditEventType.SERVICE_CREATED,
        new_value=ServiceStatus.DUE,
        metadata={
            "vehicle_id": vehicle.id,
            "cycle_number": service.cycle_number,
            "reason": status.reason.value,
        },
    )

    logger.info(
        "Vehicle %s fell due (%s); opened cycle %s",
        vehicle.registration_number,
        status.reason.value,
        service.cycle_number,
    )
    return service


def open_due_cycles(db: Session, now: datetime) -> int:
    """Open a cycle for every live vehicle that is due and has none open.

    Cheap when there is nothing to do - one query returning no rows - and it
    commits only if it opened something.
    """
    has_open_cycle = (
        select(ServiceRecord.id)
        .where(
            ServiceRecord.vehicle_id == Vehicle.id,
            ServiceRecord.status.in_(service_repository.OPEN_STATUSES),
        )
        .exists()
    )
    candidates = db.scalars(
        select(Vehicle).where(due_predicate(now.date()), ~has_open_cycle)
    ).all()

    opened = 0
    for vehicle in candidates:
        try:
            with db.begin_nested():
                if open_cycle_if_due(db, vehicle, now) is not None:
                    opened += 1
        except IntegrityError:
            # Two requests swept at once and the other opened this cycle first.
            # The unique (vehicle_id, cycle_number) constraint refused the
            # duplicate, and the savepoint discarded only this vehicle's attempt.
            logger.info("Cycle for vehicle %s was opened concurrently", vehicle.id)

    if opened:
        db.commit()
    return opened


def due_moment(status: maintenance.VehicleServiceStatus, now: datetime) -> datetime:
    """When the vehicle fell due, as precisely as the data allows.

    The date interval lands on a known day, so a cycle opened late by the sweep
    still starts its overdue clock on that day. Mileage has no timestamp of its
    own - only the write that crossed it - and that write opens the cycle
    itself, so for mileage the moment is now.
    """
    if status.reason in (maintenance.DueReason.DATE, maintenance.DueReason.BOTH):
        landed = datetime.combine(status.next_due_date, time.min, tzinfo=UTC)
        return min(landed, now)
    return now
