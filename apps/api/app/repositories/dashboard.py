"""Dashboard aggregates.

Every figure is a `COUNT` computed by PostgreSQL. Nothing here loads records so
that Python can count them, which is the failure mode the brief names, and the
frontend receives numbers rather than rows.

The predicates are imported, not rewritten. "Due" is the same expression the
fleet list filters on and "overdue" is the same one the alerts list uses,
dismissals included - a dashboard that quietly disagrees with the badge beside
it is worse than no dashboard.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.models import (
    ServiceRecord,
    ServiceStatus,
    ServiceTechnician,
    User,
    UserRole,
    Vehicle,
)
from app.repositories.alert import apply_alert_filters
from app.repositories.vehicle import due_predicate

# Eight ISO weeks ending with the current one - the current week is the eighth
# bucket, not a ninth.
WEEKS = 8

OPEN_STATUSES = (ServiceStatus.DUE, ServiceStatus.BOOKED, ServiceStatus.IN_SERVICE)


def count(db: Session, query: Select) -> int:
    return db.scalar(query) or 0


# --- vehicles ----------------------------------------------------------------


def live_vehicles(db: Session) -> int:
    return count(
        db,
        select(func.count(Vehicle.id)).where(Vehicle.is_archived.is_(False)),
    )


def archived_vehicles(db: Session) -> int:
    return count(
        db, select(func.count(Vehicle.id)).where(Vehicle.is_archived.is_(True))
    )


def due_vehicles(db: Session, today: date) -> int:
    """The same predicate GET /vehicles?due=true filters on."""
    return count(db, select(func.count(Vehicle.id)).where(due_predicate(today)))


def vehicles_in_service(db: Session) -> int:
    """Vehicles with a record currently In Service, not records."""
    return count(
        db,
        select(func.count(func.distinct(ServiceRecord.vehicle_id)))
        .join(Vehicle, Vehicle.id == ServiceRecord.vehicle_id)
        .where(
            ServiceRecord.status == ServiceStatus.IN_SERVICE,
            Vehicle.is_archived.is_(False),
        ),
    )


# --- services ----------------------------------------------------------------


def overdue_services(db: Session, grace_days: int, now: datetime) -> int:
    """Undismissed overdue records - exactly what the alert badge counts."""
    return count(
        db,
        apply_alert_filters(select(func.count(ServiceRecord.id)), grace_days, now),
    )


def open_services(db: Session) -> int:
    return count(
        db,
        select(func.count(ServiceRecord.id)).where(
            ServiceRecord.status.in_(OPEN_STATUSES)
        ),
    )


def completed_since(db: Session, start: datetime) -> int:
    return count(
        db,
        select(func.count(ServiceRecord.id)).where(
            ServiceRecord.status == ServiceStatus.COMPLETED,
            ServiceRecord.completed_at >= start,
        ),
    )


def services_by_status(db: Session) -> dict[str, int]:
    """Counts keyed by status. The caller fills in the statuses with none."""
    rows = db.execute(
        select(ServiceRecord.status, func.count(ServiceRecord.id)).group_by(
            ServiceRecord.status
        )
    ).all()
    return {status: total for status, total in rows}


def services_by_technician(db: Session) -> list[dict]:
    """Every technician, including those with nothing assigned.

    A LEFT JOIN rather than a filter, so an idle technician shows as zero
    instead of vanishing - which is the thing a manager wants to see.
    """
    open_count = func.count(
        func.distinct(
            case_when(ServiceRecord.status.in_(OPEN_STATUSES), ServiceRecord.id)
        )
    )
    completed_count = func.count(
        func.distinct(
            case_when(
                ServiceRecord.status == ServiceStatus.COMPLETED, ServiceRecord.id
            )
        )
    )

    rows = db.execute(
        select(User.id, User.full_name, open_count, completed_count)
        .outerjoin(ServiceTechnician, ServiceTechnician.technician_id == User.id)
        .outerjoin(ServiceRecord, ServiceRecord.id == ServiceTechnician.service_id)
        .where(User.role == UserRole.TECHNICIAN)
        .group_by(User.id, User.full_name)
        .order_by(User.full_name.asc())
    ).all()

    return [
        {
            "technician_id": technician_id,
            "full_name": full_name,
            "open": open_total,
            "completed": completed_total,
        }
        for technician_id, full_name, open_total, completed_total in rows
    ]


def case_when(condition, value):
    """`CASE WHEN condition THEN value END`.

    NULL otherwise, which is what makes COUNT skip it - so one query can count
    a technician's open and completed records separately.
    """
    return case((condition, value))


def completions_per_week(db: Session, weeks_starting: date) -> dict[date, int]:
    """Completions grouped by ISO week start, for weeks at or after the given one.

    ``date_trunc('week', ...)`` is ISO in PostgreSQL - it starts on Monday - so
    the bucketing is one expression rather than Python date arithmetic that has
    to be right about week boundaries twice.
    """
    week = func.date_trunc("week", ServiceRecord.completed_at)

    rows = db.execute(
        select(week.label("week_start"), func.count(ServiceRecord.id))
        .where(
            ServiceRecord.status == ServiceStatus.COMPLETED,
            ServiceRecord.completed_at.is_not(None),
            week >= weeks_starting,
        )
        .group_by(week)
        .order_by(week)
    ).all()

    return {week_start.date(): total for week_start, total in rows}
