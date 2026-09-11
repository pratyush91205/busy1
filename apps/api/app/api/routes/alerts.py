"""Overdue alerts.

An alert is not a row. It *is* an overdue service record, so there is no alert
table to create, reconcile or clean up - and nothing that can disagree with the
records themselves. What is stored is the act of dismissing one.

Manager-only throughout: this is a fleet-wide view, and a technician's world is
their own assignments.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import AppSettings, DbSession, PageQuery, require_role
from app.models import User, UserRole
from app.schemas.pagination import Page
from app.schemas.service import ServiceRead
from app.services import alert_service, maintenance

router = APIRouter(prefix="/alerts", tags=["alerts"])

Manager = Annotated[User, Depends(require_role(UserRole.FLEET_MANAGER))]


@router.get("", response_model=Page[ServiceRead])
def list_alerts(
    db: DbSession, settings: AppSettings, _: Manager, params: PageQuery
) -> Page[ServiceRead]:
    """Undismissed overdue records, longest overdue first."""
    now = maintenance.utc_now()
    grace = settings.overdue_grace_period_days

    services, total = alert_service.list_alerts(
        db, params=params, grace_days=grace, now=now
    )
    return Page[ServiceRead].build(
        [ServiceRead.of(service, grace, now) for service in services], total, params
    )


@router.get("/count")
def count_alerts(db: DbSession, settings: AppSettings, _: Manager) -> dict[str, int]:
    """Just the number, for the nav badge - one COUNT, no rows fetched."""
    return {
        "count": alert_service.count_alerts(
            db,
            grace_days=settings.overdue_grace_period_days,
            now=maintenance.utc_now(),
        )
    }


@router.post("/{service_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_alert(
    service_id: int, db: DbSession, settings: AppSettings, actor: Manager
) -> Response:
    """Hide this cycle's alert.

    The record stays Due and stays overdue: dismissing acknowledges the alert,
    it does not service the vehicle. When this cycle completes and the next one
    ages past the grace period, a new alert appears with nothing to reset -
    the dismissal points at this record, and that is a different one.
    """
    alert_service.dismiss(
        db,
        service_id,
        actor,
        grace_days=settings.overdue_grace_period_days,
        now=maintenance.utc_now(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
