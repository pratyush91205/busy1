"""Service record rules: creation, description, lifecycle, assignment, notes.

Two things hold throughout this module.

First, every mutation writes its audit event in the same transaction as the
change. There is one ``db.commit()`` per operation and the event is added
before it, so a rolled-back change cannot leave a record of having happened,
and a change cannot happen with no record of it.

Second, authorization here is per-resource - "assigned to this record" - which
is exactly what ``require_role`` cannot express. The route checks the role, and
these functions check the relationship.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import (
    AuditEventType,
    ServiceNote,
    ServiceRecord,
    ServiceStatus,
    ServiceTechnician,
    User,
    UserRole,
)
from app.repositories import audit as audit_repository
from app.repositories import service as service_repository
from app.repositories import user as user_repository
from app.repositories import vehicle as vehicle_repository
from app.schemas.pagination import PageParams
from app.schemas.service import ServiceSort, TransitionRequest
from app.schemas.vehicle import SortOrder
from app.services import due_cycles
from app.services.errors import ConflictError, ForbiddenError, NotFoundError
from app.services.lifecycle import validate_transition

logger = logging.getLogger(__name__)

# Transitions a technician assigned to the record may perform: the work they
# actually do. Booking is a manager's, because it sets the schedule.
TECHNICIAN_TRANSITIONS = frozenset(
    {ServiceStatus.IN_SERVICE, ServiceStatus.COMPLETED}
)


# --- reading -----------------------------------------------------------------


def list_services(
    db: Session,
    actor: User,
    *,
    params: PageParams,
    search: str | None = None,
    vehicle_id: int | None = None,
    status: ServiceStatus | None = None,
    technician_id: int | None = None,
    sort: ServiceSort = ServiceSort.UPDATED_AT,
    order: SortOrder = SortOrder.DESC,
    overdue: bool | None = None,
    grace_days: int = 7,
    now: datetime | None = None,
) -> tuple[list[ServiceRecord], int]:
    """A page of records, scoped to what the actor may see.

    A technician's scope is applied here, as a filter in SQL, not by fetching
    everything and dropping rows afterwards - which would also make `total`
    and the page size lie.
    """
    if now is not None:
        # A vehicle whose date interval landed since anyone last looked has its
        # cycle opened before the list is read, so the list is never behind.
        due_cycles.open_due_cycles(db, now)

    if actor.role == UserRole.TECHNICIAN:
        technician_id = actor.id

    return service_repository.list_page(
        db,
        params=params,
        search=search,
        vehicle_id=vehicle_id,
        status=status,
        technician_id=technician_id,
        sort=sort,
        order=order,
        overdue=overdue,
        grace_days=grace_days,
        now=now,
    )


def get_service(db: Session, service_id: int, actor: User) -> ServiceRecord:
    """One record the actor is allowed to see.

    A technician reaching for a record they are not assigned to gets 404, not
    403. 403 would confirm the record exists, which is a way to enumerate ids.
    """
    service = service_repository.get_by_id(db, service_id)
    if service is None:
        raise NotFoundError(f"No service record with id {service_id}")

    if actor.role == UserRole.TECHNICIAN and not service_repository.is_assigned(
        db, service_id, actor.id
    ):
        raise NotFoundError(f"No service record with id {service_id}")

    return service


def list_notes(db: Session, service_id: int, actor: User) -> list[ServiceNote]:
    get_service(db, service_id, actor)
    return service_repository.list_notes(db, service_id)


def list_timeline(db: Session, service_id: int, actor: User):
    get_service(db, service_id, actor)
    return audit_repository.list_for_service(db, service_id)


# --- creating ----------------------------------------------------------------


def create_service(
    db: Session, vehicle_id: int, description: str, actor: User
) -> ServiceRecord:
    """Open a new service cycle for a vehicle.

    Starts Due with due_since set to now, which is what the overdue clock in
    spec 06 counts from. The client does not choose the status.
    """
    vehicle = vehicle_repository.get_by_id(db, vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"No vehicle with id {vehicle_id}")

    if vehicle.is_archived:
        raise ConflictError(
            f"Vehicle {vehicle.registration_number} is archived and cannot take "
            "new service records."
        )

    open_record = service_repository.get_open_for_vehicle(db, vehicle_id)
    if open_record is not None:
        raise ConflictError(
            f"Vehicle {vehicle.registration_number} already has an open service "
            f"record (cycle {open_record.cycle_number}, {open_record.status}). "
            "Complete it before opening another."
        )

    service = ServiceRecord(
        vehicle_id=vehicle_id,
        cycle_number=service_repository.next_cycle_number(db, vehicle_id),
        description=description.strip(),
        status=ServiceStatus.DUE,
        due_since=datetime.now(UTC),
    )
    db.add(service)
    # Needed for the audit event's service_id, but still inside the
    # transaction: nothing is durable until the commit below.
    db.flush()

    audit_repository.record(
        db,
        service_id=service.id,
        actor_id=actor.id,
        event_type=AuditEventType.SERVICE_CREATED,
        new_value=ServiceStatus.DUE,
        metadata={"vehicle_id": vehicle_id, "cycle_number": service.cycle_number},
    )

    db.commit()
    logger.info(
        "Service %s (cycle %s) opened on %s by user %s",
        service.id,
        service.cycle_number,
        vehicle.registration_number,
        actor.id,
    )
    return service_repository.get_by_id(db, service.id)  # type: ignore[return-value]


def update_description(
    db: Session, service_id: int, description: str, actor: User
) -> ServiceRecord:
    """Edit the description. Nothing else on the record can change here."""
    service = get_service(db, service_id, actor)
    require_manager_or_assigned(db, service, actor, "edit this service record")

    service.description = description.strip()
    db.commit()

    logger.info("Service %s description edited by user %s", service_id, actor.id)
    return service_repository.get_by_id(db, service_id)  # type: ignore[return-value]


# --- lifecycle ---------------------------------------------------------------


def transition(
    db: Session, service_id: int, request: TransitionRequest, actor: User
) -> ServiceRecord:
    """Move a record along the lifecycle, or refuse and say why.

    Everything the transition touches - the status, the completion data, the
    vehicle's odometer and the audit event - commits together or not at all.
    """
    service = get_service(db, service_id, actor)
    target = request.status

    validate_transition(service.status, target)
    require_permitted_transition(db, service, target, actor)

    if request.technician_id is not None and target is not ServiceStatus.BOOKED:
        raise ConflictError(
            "A technician is named when booking. To change who is assigned "
            "after that, use the assignment endpoints."
        )

    metadata: dict = {}

    if target is ServiceStatus.BOOKED:
        if request.scheduled_date is None:
            raise ConflictError("Booking a service requires a scheduled date.")
        book_technician(db, service, request.technician_id, actor, metadata)
        service.scheduled_date = request.scheduled_date
        metadata["scheduled_date"] = request.scheduled_date.isoformat()

    if target is ServiceStatus.COMPLETED:
        complete(db, service, request, metadata)

    previous = service.status
    service.status = target

    audit_repository.record(
        db,
        service_id=service.id,
        actor_id=actor.id,
        event_type=AuditEventType.STATUS_CHANGED,
        old_value=previous,
        new_value=target,
        metadata=metadata or None,
    )

    db.commit()
    logger.info(
        "Service %s moved %s -> %s by user %s", service_id, previous, target, actor.id
    )
    return service_repository.get_by_id(db, service_id)  # type: ignore[return-value]


def complete(
    db: Session, service: ServiceRecord, request: TransitionRequest, metadata: dict
) -> None:
    """The completion half of a transition, inside the caller's transaction.

    Closes this cycle and sets up the next one: the completion odometer and
    completed_at are what spec 06 counts the next interval from, so clearing
    due_since here is what stops a completed record still looking overdue.
    """
    if request.completion_odometer is None:
        raise ConflictError("Completing a service requires the completion odometer.")

    vehicle = service.vehicle
    if request.completion_odometer < vehicle.current_odometer:
        raise ConflictError(
            f"Completion odometer {request.completion_odometer} is lower than "
            f"the vehicle's current reading {vehicle.current_odometer}."
        )

    service.completed_at = datetime.now(UTC)
    service.completion_odometer = request.completion_odometer
    # The service just recorded a newer reading than the vehicle had.
    vehicle.current_odometer = request.completion_odometer
    # And the next cycle counts from here - both counters - rather than from
    # the original vehicle creation. This is the reset the brief asks for.
    vehicle.service_baseline_odometer = request.completion_odometer
    vehicle.service_baseline_date = service.completed_at.date()
    # This cycle is over, so it is no longer due or overdue.
    service.due_since = None

    metadata["completion_odometer"] = request.completion_odometer



def book_technician(
    db: Session,
    service: ServiceRecord,
    technician_id: int | None,
    actor: User,
    metadata: dict,
) -> None:
    """The technician half of booking, inside the caller's transaction.

    Booking assigns a scheduled date *and* a technician, so a record cannot be
    booked with nobody on it. The technician can be named in the booking -
    assigned here, with its own audit event landing ahead of the status change -
    or already be assigned.
    """
    if technician_id is not None:
        if not service_repository.is_assigned(db, service.id, technician_id):
            add_assignment(db, service.id, technician_id, actor)
        metadata["technician_id"] = technician_id
        return

    if not service.technicians:
        raise ConflictError(
            "Booking a service requires a technician. Name one when booking, "
            "or assign one to the record first."
        )

# --- assignment --------------------------------------------------------------


def assign_technician(
    db: Session, service_id: int, technician_id: int, actor: User
) -> ServiceRecord:
    service = get_service(db, service_id, actor)
    require_open_for_assignment(service)

    technician = add_assignment(db, service_id, technician_id, actor, strict=True)

    db.commit()
    logger.info(
        "Technician %s assigned to service %s by user %s",
        technician_id,
        service_id,
        actor.id,
    )
    return service_repository.get_by_id(db, service_id)  # type: ignore[return-value]


def unassign_technician(
    db: Session, service_id: int, technician_id: int, actor: User
) -> None:
    service = get_service(db, service_id, actor)
    require_open_for_assignment(service)

    if not service_repository.is_assigned(db, service_id, technician_id):
        raise NotFoundError(
            f"User {technician_id} is not assigned to this service record."
        )

    technician = user_repository.get_by_id(db, technician_id)
    assignment = db.get(ServiceTechnician, (service_id, technician_id))
    db.delete(assignment)

    audit_repository.record(
        db,
        service_id=service_id,
        actor_id=actor.id,
        event_type=AuditEventType.TECHNICIAN_UNASSIGNED,
        old_value=str(technician_id),
        metadata={"technician_name": technician.full_name if technician else None},
    )

    db.commit()
    logger.info(
        "Technician %s unassigned from service %s by user %s",
        technician_id,
        service_id,
        actor.id,
    )



def add_assignment(
    db: Session,
    service_id: int,
    technician_id: int,
    actor: User,
    *,
    strict: bool = False,
) -> User:
    """Assign one technician and record it, without committing.

    Shared by the assignment endpoint and by booking, so the two cannot
    disagree about who may be assigned or what the timeline says. ``strict``
    refuses a technician who is already assigned; booking checks that itself.
    """
    technician = user_repository.get_by_id(db, technician_id)
    if technician is None:
        raise NotFoundError(f"No user with id {technician_id}")

    if technician.role != UserRole.TECHNICIAN:
        raise ConflictError(
            f"{technician.full_name} is a {technician.role} and cannot be "
            "assigned to service work."
        )

    if strict and service_repository.is_assigned(db, service_id, technician_id):
        raise ConflictError(
            f"{technician.full_name} is already assigned to this service record."
        )

    db.add(ServiceTechnician(service_id=service_id, technician_id=technician_id))
    audit_repository.record(
        db,
        service_id=service_id,
        actor_id=actor.id,
        event_type=AuditEventType.TECHNICIAN_ASSIGNED,
        new_value=str(technician_id),
        metadata={"technician_name": technician.full_name},
    )
    return technician

# --- notes -------------------------------------------------------------------


def add_note(db: Session, service_id: int, content: str, actor: User) -> ServiceNote:
    service = get_service(db, service_id, actor)
    require_manager_or_assigned(db, service, actor, "add a note to this record")

    note = ServiceNote(
        service_id=service_id, author_id=actor.id, content=content.strip()
    )
    db.add(note)
    db.flush()

    audit_repository.record(
        db,
        service_id=service_id,
        actor_id=actor.id,
        event_type=AuditEventType.NOTE_ADDED,
        new_value=str(note.id),
    )

    db.commit()
    logger.info("Note %s added to service %s by user %s", note.id, service_id, actor.id)
    return note


# --- rules -------------------------------------------------------------------


def require_manager_or_assigned(
    db: Session, service: ServiceRecord, actor: User, action: str
) -> None:
    """The per-resource check ``require_role`` cannot express."""
    if actor.role == UserRole.FLEET_MANAGER:
        return
    if service_repository.is_assigned(db, service.id, actor.id):
        return
    raise ForbiddenError(f"You must be assigned to this record to {action}.")


def require_permitted_transition(
    db: Session, service: ServiceRecord, target: ServiceStatus, actor: User
) -> None:
    if actor.role == UserRole.FLEET_MANAGER:
        return

    if not service_repository.is_assigned(db, service.id, actor.id):
        raise ForbiddenError(
            "You must be assigned to this record to change its status."
        )

    if target not in TECHNICIAN_TRANSITIONS:
        raise ForbiddenError(
            "Booking a service is a fleet manager's action - it sets the schedule."
        )


def require_open_for_assignment(service: ServiceRecord) -> None:
    if service.status == ServiceStatus.COMPLETED:
        raise ConflictError(
            "This service record is completed. Its assignments are part of its "
            "history and cannot be changed."
        )
