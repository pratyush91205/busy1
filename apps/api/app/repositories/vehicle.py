"""Database access for vehicles.

Filtering, sorting and paging are SQL. Nothing here loads the fleet and narrows
it in Python - that is the failure mode the brief calls out by name, and it is
also the one that looks fine until the seed data grows.
"""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import Vehicle
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
) -> tuple[list[Vehicle], int]:
    """One page of vehicles, and how many match the filter overall."""
    query = apply_filters(select(Vehicle), search=search, include_archived=include_archived)

    total = db.scalar(
        apply_filters(
            select(func.count(Vehicle.id)),
            search=search,
            include_archived=include_archived,
        )
    )

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
    query: Select, *, search: str | None, include_archived: bool
) -> Select:
    if not include_archived:
        query = query.where(Vehicle.is_archived.is_(False))

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


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
