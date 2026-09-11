"""The fleet dashboard.

One endpoint rather than six. The dashboard is one screen, so six round trips
to paint it would be six chances for a half-drawn answer, and the queries are
all indexed counts.

Manager only: a fleet-wide summary is not a technician's view.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import AppSettings, DbSession, require_role
from app.models import User, UserRole
from app.services import dashboard_service, maintenance

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

Manager = Annotated[User, Depends(require_role(UserRole.FLEET_MANAGER))]


class VehicleCounts(BaseModel):
    total: int
    due: int
    in_service: int
    archived: int


class ServiceCounts(BaseModel):
    overdue: int
    open: int
    completed_this_week: int


class StatusCount(BaseModel):
    status: str
    count: int


class TechnicianWorkload(BaseModel):
    technician_id: int
    full_name: str
    open: int
    completed: int


class WeekCount(BaseModel):
    week_start: str
    count: int


class DashboardRead(BaseModel):
    vehicles: VehicleCounts
    services: ServiceCounts
    by_status: list[StatusCount]
    by_technician: list[TechnicianWorkload]
    # Exactly eight buckets, oldest first, zeros included - a chart that drops
    # empty weeks says the fleet was busy every week.
    completed_per_week: list[WeekCount]


@router.get("", response_model=DashboardRead)
def read_dashboard(
    db: DbSession, settings: AppSettings, _: Manager
) -> DashboardRead:
    summary = dashboard_service.build(
        db,
        grace_days=settings.overdue_grace_period_days,
        now=maintenance.utc_now(),
    )
    return DashboardRead(
        vehicles=VehicleCounts(**summary.vehicles),
        services=ServiceCounts(**summary.services),
        by_status=[StatusCount(**row) for row in summary.by_status],
        by_technician=[TechnicianWorkload(**row) for row in summary.by_technician],
        completed_per_week=[WeekCount(**row) for row in summary.completed_per_week],
    )
