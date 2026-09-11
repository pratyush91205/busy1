"""Bulk odometer upload and service history export.

Both are fleet-manager only and both are server-side: the upload is parsed and
applied here, and the export is generated here and streamed. Neither is
assembled in the browser.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import AppSettings, DbSession, require_role
from app.models import User, UserRole
from app.models.enums import ServiceStatus
from app.schemas.service import OdometerUploadReport
from app.services import export_service, maintenance, odometer_upload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])

Manager = Annotated[User, Depends(require_role(UserRole.FLEET_MANAGER))]


@router.post("/vehicles/odometer-upload", response_model=OdometerUploadReport)
async def upload_odometer_readings(
    db: DbSession,
    actor: Manager,
    file: Annotated[UploadFile, File()],
) -> OdometerUploadReport:
    """Apply a CSV of readings, and report on every row.

    Returns 200 even when rows were rejected: a mixed file is a normal outcome,
    not an error. Only a missing or malformed header is a whole-file 422, and
    that is because the file is not the thing this endpoint takes.

    There is no transaction around the file. Valid rows are applied even when
    others fail - a depot upload where one row is a typo must not discard the
    other forty-nine.
    """
    report = odometer_upload.process(db, await file.read(), actor)
    return OdometerUploadReport(
        total=report.total,
        succeeded=report.succeeded,
        failed=report.failed,
        results=[result.__dict__ for result in report.results],
    )


@router.get("/services/export.csv")
def export_service_history(
    db: DbSession,
    settings: AppSettings,
    _: Manager,
    search: Annotated[str | None, Query(max_length=200)] = None,
    vehicle_id: int | None = None,
    status_filter: Annotated[ServiceStatus | None, Query(alias="status")] = None,
    technician_id: int | None = None,
    overdue: bool | None = None,
) -> StreamingResponse:
    """The service history as CSV, streamed.

    Takes the same filters as GET /services, so "export what I am looking at"
    is the same query without the paging.
    """
    now = maintenance.utc_now()

    rows = export_service.stream_csv(
        db,
        grace_days=settings.overdue_grace_period_days,
        now=now,
        search=search,
        vehicle_id=vehicle_id,
        status=status_filter,
        technician_id=technician_id,
        overdue=overdue,
    )

    filename = f"service-history-{now.date().isoformat()}.csv"
    return StreamingResponse(
        rows,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
