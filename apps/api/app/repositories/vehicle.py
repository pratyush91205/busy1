"""Database access for vehicles.

Filtering, sorting and paging are SQL. Nothing here loads the fleet and narrows
it in Python - that is the failure mode the brief calls out by name, and it is
also the one that looks fine until the seed data grows.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Select, and_, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models import ServiceRecord, ServiceStatus, Vehicle
from app.schemas.pagination import PageParams
from app.schemas.vehicle import SortOrder, VehicleSort

SORT_COLUMNS = {
    VehicleSort.REGISTRATION_NUMBER: Vehicle.registration_number,
    VehicleSort.CURRENT_ODOMETER: Vehicle.current_odometer,
    VehicleSort.CREATED_AT: Vehicle.created_at,
    VehicleSort.UPDATED_AT: Vehicle.updated_at,
}


def get_by_id(db: Session, vehicle_id: int) -> Vehicle | None:
    return db.get(Vehicle, vehicle_id)


def get_by_registration(db: Session, registration_number: str) -> Vehicle | None:
    """Find by exact registration.

    Callers pass an already-normalised value; the column stores the normalised
    form, so this is an index lookup rather than a function scan.
    """
    return db.scalars(
        select(Vehicle).where(Vehicle.registration_number == registration_number)
    ).first()


def list_page(
    db: Session,
    *,
    params: PageParams,
    search: str | None = None,
    include_archived: bool = False,
    sort: VehicleSort = VehicleSort.REGISTRATION_NUMBER,
    order: SortOrder = SortOrder.ASC,
    due: bool | None = None,
    today: date | None = None,
) -> tuple[list[Vehicle], int]:
    """One page of vehicles, and how many match the filter overall."""
    filters = dict(
        search=search, include_archived=include_archived, due=due, today=today
    )
    query = apply_filters(select(Vehicle), **filters)

    total = db.scalar(apply_filters(select(func.count(Vehicle.id)), **filters))

    column = SORT_COLUMNS[sort]
    ordering = column.asc() if order is SortOrder.ASC else column.desc()
    # Registration breaks ties. Without a tiebreaker, two vehicles with the
    # same odometer can swap places between pages and one of them is never seen.
    page = db.scalars(
        query.order_by(ordering, Vehicle.registration_number.asc())
        .offset(params.offset)
        .limit(params.limit)
    ).all()

    return list(page), total or 0


def apply_filters(
    query: Select,
    *,
    search: str | None,
    include_archived: bool,
    due: bool | None = None,
    today: date | None = None,
) -> Select:
    if not include_archived:
        query = query.where(Vehicle.is_archived.is_(False))

    if due is not None and today is not None:
        query = query.where(due_predicate(today) if due else ~due_predicate(today))

    if search:
        # Escape the LIKE wildcards, or a search for "%" matches the fleet.
        term = f"%{escape_like(search.strip())}%"
        query = query.where(
            or_(
                Vehicle.registration_number.ilike(term, escape="\\"),
                Vehicle.make.ilike(term, escape="\\"),
                Vehicle.model.ilike(term, escape="\\"),
            )
        )

    return query


def due_predicate(today: date):
    """A vehicle is due when EITHER interval is reached, not both.

    A single-table predicate, which is exactly why the cycle baseline is
    stored: deriving the date side would need a lateral join to the newest
    completed record on every row of the fleet.

    The date comparison is integer arithmetic - in PostgreSQL, date minus date
    is a number of days - rather than building an interval, so it reads the
    same way the rule is written: days elapsed since the cycle began has
    reached the interval.
    """
    days_elapsed = literal(today, Date) - Vehicle.service_baseline_date
    reached_date = days_elapsed >= Vehicle.service_date_interval
    reached_mileage = (
        Vehicle.current_odometer
        >= Vehicle.service_baseline_odometer + Vehicle.service_mileage_interval
    )

    # An archived vehicle is not in service, so it is never due.
    return and_(
        Vehicle.is_archived.is_(False), or_(reached_date, reached_mileage)
    )


def vehicle_ids_with_open_record(db: Session, vehicle_ids: list[int]) -> set[int]:
    """Which of these vehicles have a cycle open, in one query.

    Asking per vehicle would be an N+1 on every page of the fleet list.
    """
    if not vehicle_ids:
        return set()
    return set(
        db.scalars(
            select(ServiceRecord.vehicle_id)
            .where(
                ServiceRecord.vehicle_id.in_(vehicle_ids),
                ServiceRecord.status.in_(
                    (ServiceStatus.DUE, ServiceStatus.BOOKED, ServiceStatus.IN_SERVICE)
                ),
            )
            .distinct()
        ).all()
    )


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
