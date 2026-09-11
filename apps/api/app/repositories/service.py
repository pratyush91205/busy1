"""Database access for service records.

The relationships are declared ``lazy="raise_on_sql"``, so every read path here
must say what it loads. That is the point: a list of 20 records each
lazy-loading its vehicle and technicians is 41 queries, and the version that
raises is the one that gets noticed in a test rather than in production.
"""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import ServiceNote, ServiceRecord, ServiceStatus, ServiceTechnician
from app.repositories.vehicle import escape_like
from app.schemas.pagination import PageParams
from app.schemas.service import ServiceSort
from app.schemas.vehicle import SortOrder

SORT_COLUMNS = {
    ServiceSort.SCHEDULED_DATE: ServiceRecord.scheduled_date,
    ServiceSort.STATUS: ServiceRecord.status,
    ServiceSort.UPDATED_AT: ServiceRecord.updated_at,
}

# Anything that is not completed is an open cycle.
OPEN_STATUSES = (
    ServiceStatus.DUE,
    ServiceStatus.BOOKED,
    ServiceStatus.IN_SERVICE,
)


def with_relations(query: Select) -> Select:
    return query.options(
        selectinload(ServiceRecord.vehicle),
        selectinload(ServiceRecord.technicians),
    )


def get_by_id(db: Session, service_id: int) -> ServiceRecord | None:
    return db.scalars(
        with_relations(select(ServiceRecord).where(ServiceRecord.id == service_id))
    ).first()


def get_open_for_vehicle(db: Session, vehicle_id: int) -> ServiceRecord | None:
    """The vehicle's current cycle, if it has one.

    One open record per vehicle is a rule the service layer enforces; this is
    how it checks, and how "the current cycle" is defined for spec 06.
    """
    return db.scalars(
        select(ServiceRecord)
        .where(
            ServiceRecord.vehicle_id == vehicle_id,
            ServiceRecord.status.in_(OPEN_STATUSES),
        )
        .order_by(ServiceRecord.cycle_number.desc())
    ).first()


def next_cycle_number(db: Session, vehicle_id: int) -> int:
    """One past the vehicle's highest cycle, or 1.

    A concurrent double-create still produces the same number twice; the unique
    constraint on (vehicle_id, cycle_number) is what turns that into an error
    rather than two records both calling themselves cycle 3.
    """
    highest = db.scalar(
        select(func.max(ServiceRecord.cycle_number)).where(
            ServiceRecord.vehicle_id == vehicle_id
        )
    )
    return (highest or 0) + 1


def last_completed_for_vehicle(db: Session, vehicle_id: int) -> ServiceRecord | None:
    """The most recent completed service - where the next cycle counts from."""
    return db.scalars(
        select(ServiceRecord)
        .where(
            ServiceRecord.vehicle_id == vehicle_id,
            ServiceRecord.status == ServiceStatus.COMPLETED,
        )
        .order_by(ServiceRecord.completed_at.desc(), ServiceRecord.id.desc())
    ).first()


def is_assigned(db: Session, service_id: int, technician_id: int) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(ServiceTechnician)
            .where(
                ServiceTechnician.service_id == service_id,
                ServiceTechnician.technician_id == technician_id,
            )
        )
        or 0
    ) > 0


def list_page(
    db: Session,
    *,
    params: PageParams,
    search: str | None = None,
    vehicle_id: int | None = None,
    status: ServiceStatus | None = None,
    technician_id: int | None = None,
    sort: ServiceSort = ServiceSort.UPDATED_AT,
    order: SortOrder = SortOrder.DESC,
) -> tuple[list[ServiceRecord], int]:
    filters = dict(
        search=search, vehicle_id=vehicle_id, status=status, technician_id=technician_id
    )

    total = db.scalar(
        apply_filters(select(func.count(ServiceRecord.id.distinct())), **filters)
    )

    column = SORT_COLUMNS[sort]
    ordering = column.asc() if order is SortOrder.ASC else column.desc()

    page = db.scalars(
        with_relations(apply_filters(select(ServiceRecord), **filters))
        # id breaks ties, or records sharing a scheduled_date can swap between
        # pages and one of them is never seen.
        .order_by(ordering, ServiceRecord.id.desc())
        .offset(params.offset)
        .limit(params.limit)
    ).all()

    return list(page), total or 0


def apply_filters(
    query: Select,
    *,
    search: str | None,
    vehicle_id: int | None,
    status: ServiceStatus | None,
    technician_id: int | None,
) -> Select:
    if vehicle_id is not None:
        query = query.where(ServiceRecord.vehicle_id == vehicle_id)

    if status is not None:
        query = query.where(ServiceRecord.status == status)

    if technician_id is not None:
        # EXISTS rather than a join: a join to the assignment table would
        # duplicate a record that has several technicians, which inflates the
        # count and the page.
        query = query.where(
            select(ServiceTechnician.service_id)
            .where(
                ServiceTechnician.service_id == ServiceRecord.id,
                ServiceTechnician.technician_id == technician_id,
            )
            .exists()
        )

    if search:
        term = f"%{escape_like(search.strip())}%"
        query = query.where(or_(ServiceRecord.description.ilike(term, escape="\\")))

    return query


def list_notes(db: Session, service_id: int) -> list[ServiceNote]:
    return list(
        db.scalars(
            select(ServiceNote)
            .options(selectinload(ServiceNote.author))
            .where(ServiceNote.service_id == service_id)
            .order_by(ServiceNote.created_at.asc(), ServiceNote.id.asc())
        ).all()
    )
