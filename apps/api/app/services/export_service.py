"""Service history export.

Generated row by row from a server-side cursor and yielded as it goes, rather
than built into one string and returned. At fleet scale either would work; the
streaming version is what stops this becoming the endpoint that falls over
first when the data grows, and it costs nothing to write that way now.

Nothing here is assembled in the browser, which is the failure mode the brief
names.
"""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ServiceRecord, ServiceStatus
from app.repositories import service as service_repository
from app.schemas.service import ServiceSort
from app.schemas.vehicle import SortOrder
from app.services import maintenance

logger = logging.getLogger(__name__)

COLUMNS = (
    "registration_number",
    "make",
    "model",
    "cycle_number",
    "description",
    "status",
    "is_overdue",
    "scheduled_date",
    "completed_at",
    "completion_odometer",
    "technicians",
    "created_at",
)

# Rows per database round trip. Large enough that the query is not the
# bottleneck, small enough that memory stays flat however big the fleet gets.
CHUNK = 500


def stream_csv(
    db: Session,
    *,
    grace_days: int,
    now: datetime,
    search: str | None = None,
    vehicle_id: int | None = None,
    status: ServiceStatus | None = None,
    technician_id: int | None = None,
    overdue: bool | None = None,
) -> Iterator[str]:
    """Yield the export one row at a time, header first."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(COLUMNS)
    yield take(buffer)

    query = service_repository.with_relations(
        service_repository.apply_filters(
            select(ServiceRecord),
            search=search,
            vehicle_id=vehicle_id,
            status=status,
            technician_id=technician_id,
            overdue=overdue,
            grace_days=grace_days,
            now=now,
        )
    ).order_by(ServiceRecord.id.asc())

    exported = 0
    for service in db.scalars(query).yield_per(CHUNK):
        writer.writerow(row_for(service, grace_days, now))
        exported += 1
        yield take(buffer)

    logger.info("Exported %s service records", exported)


def row_for(service: ServiceRecord, grace_days: int, now: datetime) -> list:
    return [
        service.vehicle.registration_number,
        service.vehicle.make,
        service.vehicle.model,
        service.cycle_number,
        service.description,
        service.status,
        # Overdue is derived, so it is computed here rather than read off a
        # column that does not exist.
        "yes" if maintenance.is_overdue(service, grace_days, now) else "no",
        iso(service.scheduled_date),
        iso(service.completed_at),
        service.completion_odometer if service.completion_odometer is not None else "",
        # One cell, because a CSV column cannot hold a list and a spreadsheet
        # user would rather read names than join two files.
        "; ".join(technician.full_name for technician in service.technicians),
        iso(service.created_at),
    ]


def iso(value) -> str:
    """ISO-8601 UTC, matching the rest of the API. Empty for null."""
    return value.isoformat() if value is not None else ""


def take(buffer: io.StringIO) -> str:
    """Drain the buffer, so memory does not grow with the export."""
    value = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    return value
