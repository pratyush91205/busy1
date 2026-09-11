"""Service record routes.

Thin. Role checks are dependencies, per-resource checks ("assigned to this
record") happen in the service layer, and every rule refusal arrives as a
domain error that the handler in ``app.main`` turns into a status code.

Two absences are deliberate and load-bearing:

* no route updates or deletes an audit event, and
* no route updates or deletes a note.

Both are append-only, and for audit events the database refuses it as well.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUser, DbSession, PageQuery, require_role
from app.models import User, UserRole
from app.models.enums import ServiceStatus
from app.schemas.pagination import Page
from app.schemas.service import (
    AssignTechnicianRequest,
    AuditEventRead,
    NoteCreate,
    NoteRead,
    ServiceCreate,
    ServiceRead,
    ServiceSort,
    ServiceUpdate,
    TransitionRequest,
)
from app.schemas.vehicle import SortOrder
from app.services import service_service

router = APIRouter(prefix="/services", tags=["services"])

Manager = Annotated[User, Depends(require_role(UserRole.FLEET_MANAGER))]


@router.get("", response_model=Page[ServiceRead])
def list_services(
    db: DbSession,
    actor: CurrentUser,
    params: PageQuery,
    search: Annotated[str | None, Query(max_length=200)] = None,
    vehicle_id: int | None = None,
    status_filter: Annotated[ServiceStatus | None, Query(alias="status")] = None,
    technician_id: int | None = None,
    sort: ServiceSort = ServiceSort.UPDATED_AT,
    order: SortOrder = SortOrder.DESC,
) -> Page[ServiceRead]:
    # A technician's scope is applied in the service layer, in SQL, so `total`
    # and the page size describe what they can actually see.
    services, total = service_service.list_services(
        db,
        actor,
        params=params,
        search=search,
        vehicle_id=vehicle_id,
        status=status_filter,
        technician_id=technician_id,
        sort=sort,
        order=order,
    )
    return Page[ServiceRead].build(
        [ServiceRead.model_validate(service) for service in services], total, params
    )


@router.get("/{service_id}", response_model=ServiceRead)
def read_service(service_id: int, db: DbSession, actor: CurrentUser) -> ServiceRead:
    return ServiceRead.model_validate(
        service_service.get_service(db, service_id, actor)
    )


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate, db: DbSession, actor: Manager
) -> ServiceRead:
    return ServiceRead.model_validate(
        service_service.create_service(
            db, payload.vehicle_id, payload.description, actor
        )
    )


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int, payload: ServiceUpdate, db: DbSession, actor: CurrentUser
) -> ServiceRead:
    """Description only.

    The schema has no status, vehicle or technician field, so an assigned
    technician editing a description cannot reassign the record through the
    same call.
    """
    return ServiceRead.model_validate(
        service_service.update_description(db, service_id, payload.description, actor)
    )


@router.post("/{service_id}/transition", response_model=ServiceRead)
def transition_service(
    service_id: int, payload: TransitionRequest, db: DbSession, actor: CurrentUser
) -> ServiceRead:
    """One endpoint for the whole lifecycle; the target status is data.

    Who may make a given move depends on the move, so the check is in the
    service layer rather than a role dependency here.
    """
    return ServiceRead.model_validate(
        service_service.transition(db, service_id, payload, actor)
    )


@router.post("/{service_id}/technicians", response_model=ServiceRead)
def assign_technician(
    service_id: int,
    payload: AssignTechnicianRequest,
    db: DbSession,
    actor: Manager,
) -> ServiceRead:
    return ServiceRead.model_validate(
        service_service.assign_technician(
            db, service_id, payload.technician_id, actor
        )
    )


@router.delete(
    "/{service_id}/technicians/{technician_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unassign_technician(
    service_id: int, technician_id: int, db: DbSession, actor: Manager
) -> Response:
    service_service.unassign_technician(db, service_id, technician_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{service_id}/notes", response_model=list[NoteRead])
def list_notes(
    service_id: int, db: DbSession, actor: CurrentUser
) -> list[NoteRead]:
    return [
        NoteRead.model_validate(note)
        for note in service_service.list_notes(db, service_id, actor)
    ]


@router.post(
    "/{service_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED
)
def add_note(
    service_id: int, payload: NoteCreate, db: DbSession, actor: CurrentUser
) -> NoteRead:
    note = service_service.add_note(db, service_id, payload.content, actor)
    # Re-read through the list so the author relationship is loaded; the
    # relationships raise rather than lazy-load by design.
    return NoteRead.model_validate(
        next(
            item
            for item in service_service.list_notes(db, service_id, actor)
            if item.id == note.id
        )
    )


@router.get("/{service_id}/timeline", response_model=list[AuditEventRead])
def read_timeline(
    service_id: int, db: DbSession, actor: CurrentUser
) -> list[AuditEventRead]:
    """The immutable audit trail, oldest first. Read-only, by design."""
    return [
        AuditEventRead.model_validate(event)
        for event in service_service.list_timeline(db, service_id, actor)
    ]
