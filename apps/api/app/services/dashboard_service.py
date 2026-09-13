"""The dashboard summary.

Assembles the aggregates and fills in the gaps the database cannot: a status
with no records, a week with no completions, a technician with nothing
assigned. Each of those has to appear as a zero rather than be absent, or the
screen tells the reader the fleet was busy every week.

Week boundaries are ISO-8601 in UTC - Monday 00:00 to Sunday 23:59:59 - and the
database session is pinned to UTC, so the Python and SQL halves agree about
where a week starts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ServiceStatus
from app.repositories import dashboard as dashboard_repository
from app.services import due_cycles

WEEKS = dashboard_repository.WEEKS


@dataclass(frozen=True)
class Summary:
    vehicles: dict
    services: dict
    by_status: list[dict]
    by_technician: list[dict]
    completed_per_week: list[dict]


def week_start(moment: datetime) -> date:
    """The Monday of the ISO week containing ``moment``, in UTC."""
    day = moment.astimezone(UTC).date()
    return day - timedelta(days=day.weekday())


def build(db: Session, *, grace_days: int, now: datetime) -> Summary:
    due_cycles.open_due_cycles(db, now)
    this_week = week_start(now)
    # Eight buckets ending with the current week, so the current one is the
    # eighth rather than a ninth.
    earliest_week = this_week - timedelta(weeks=WEEKS - 1)

    counts = dashboard_repository.services_by_status(db)
    per_week = dashboard_repository.completions_per_week(db, earliest_week)

    return Summary(
        vehicles={
            "total": dashboard_repository.live_vehicles(db),
            "due": dashboard_repository.due_vehicles(db),
            "in_service": dashboard_repository.vehicles_in_service(db),
            "archived": dashboard_repository.archived_vehicles(db),
        },
        services={
            "overdue": dashboard_repository.overdue_services(db, grace_days, now),
            "open": dashboard_repository.open_services(db),
            "completed_this_week": dashboard_repository.completed_since(
                db, datetime.combine(this_week, datetime.min.time(), tzinfo=UTC)
            ),
        },
        # All four stored statuses, including the ones at zero. Overdue is not
        # here: it is derived, and lives under services.
        by_status=[
            {"status": status.value, "count": counts.get(status.value, 0)}
            for status in ServiceStatus
        ],
        by_technician=dashboard_repository.services_by_technician(db),
        completed_per_week=[
            {
                "week_start": (earliest_week + timedelta(weeks=offset)).isoformat(),
                "count": per_week.get(earliest_week + timedelta(weeks=offset), 0),
            }
            for offset in range(WEEKS)
        ],
    )
