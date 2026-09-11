"""Overdue records, and the dismissals against them.

There is no table of alerts. An alert *is* an overdue record, so there is
nothing to create, reconcile or clean up, and nothing that can disagree with
the records themselves.

The overdue predicate is SQL rather than a Python filter, because it drives the
list and the count. Filtering in Python would make ``total`` and the badge
describe different things from the page.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import OverdueAlertDismissal, ServiceRecord, ServiceStatus
from app.repositories.service import with_relations
from app.schemas.pagination import PageParams


def overdue_predicate(grace_days: int, now: datetime):
    """status is Due, and the grace period has elapsed since it became Due.

    The threshold is computed here rather than in the query so PostgreSQL
    compares against a plain timestamp, which the (status, due_since) index
    can serve.
    """
    threshold = now - timedelta(days=grace_days)
    return (
        ServiceRecord.status == ServiceStatus.DUE,
        ServiceRecord.due_since.is_not(None),
        ServiceRecord.due_since <= threshold,
    )


def not_dismissed():
    """No dismissal row points at this record.

    Cycle-scoped for free: one record is one cycle, so the next cycle is a
    different record with no dismissal against it and its alert appears without
    anything needing to reset.
    """
    return ~select(OverdueAlertDismissal.id).where(
        OverdueAlertDismissal.service_id == ServiceRecord.id
    ).exists()


def apply_alert_filters(query: Select, grace_days: int, now: datetime) -> Select:
    return query.where(*overdue_predicate(grace_days, now), not_dismissed())


def list_alerts(
    db: Session, *, params: PageParams, grace_days: int, now: datetime
) -> tuple[list[ServiceRecord], int]:
    """Undismissed overdue records, longest overdue first."""
    total = db.scalar(
        apply_alert_filters(select(func.count(ServiceRecord.id)), grace_days, now)
    )

    page = db.scalars(
        apply_alert_filters(with_relations(select(ServiceRecord)), grace_days, now)
        .order_by(ServiceRecord.due_since.asc(), ServiceRecord.id.asc())
        .offset(params.offset)
        .limit(params.limit)
    ).all()

    return list(page), total or 0


def count_alerts(db: Session, *, grace_days: int, now: datetime) -> int:
    """Just the number, for the nav badge. One COUNT, no rows fetched."""
    return (
        db.scalar(
            apply_alert_filters(select(func.count(ServiceRecord.id)), grace_days, now)
        )
        or 0
    )


def get_dismissal(db: Session, service_id: int) -> OverdueAlertDismissal | None:
    return db.scalars(
        select(OverdueAlertDismissal).where(
            OverdueAlertDismissal.service_id == service_id
        )
    ).first()
