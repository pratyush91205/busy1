"""Overdue alerts and their dismissal.

Dismissing hides the alert. It does not fix the maintenance: the record is
still Due and still overdue afterwards, and a test asserts exactly that.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import OverdueAlertDismissal, ServiceRecord, User
from app.repositories import alert as alert_repository
from app.repositories import service as service_repository
from app.schemas.pagination import PageParams
from app.services import due_cycles, maintenance
from app.services.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


def list_alerts(
    db: Session, *, params: PageParams, grace_days: int, now: datetime
) -> tuple[list[ServiceRecord], int]:
    # A vehicle left unbooked past its date interval must alert even if nobody
    # has opened its record - that is the vehicle the alert exists for.
    due_cycles.open_due_cycles(db, now)
    return alert_repository.list_alerts(
        db, params=params, grace_days=grace_days, now=now
    )


def count_alerts(db: Session, *, grace_days: int, now: datetime) -> int:
    due_cycles.open_due_cycles(db, now)
    return alert_repository.count_alerts(db, grace_days=grace_days, now=now)


def dismiss(
    db: Session, service_id: int, actor: User, *, grace_days: int, now: datetime
) -> None:
    """Dismiss the alert for one service cycle.

    Scoped to the cycle by construction: the dismissal points at the record,
    and the next cycle is a different record. Nothing has to remember to reset.
    """
    service = service_repository.get_by_id(db, service_id)
    if service is None:
        raise NotFoundError(f"No service record with id {service_id}")

    if not maintenance.is_overdue(service, grace_days, now):
        # Refusing rather than accepting silently: dismissing something that is
        # not raising an alert means the caller is confused about which record
        # they are looking at.
        raise ConflictError(
            "That service record is not overdue, so it has no alert to dismiss."
        )

    if alert_repository.get_dismissal(db, service_id) is not None:
        raise ConflictError("That alert has already been dismissed.")

    db.add(
        OverdueAlertDismissal(service_id=service_id, dismissed_by=actor.id)
    )
    db.commit()

    logger.info("Alert for service %s dismissed by user %s", service_id, actor.id)
