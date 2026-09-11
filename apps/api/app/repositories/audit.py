"""Writing and reading the immutable service timeline.

``record`` adds to the session but never commits. That is deliberate: an audit
event must land in the same transaction as the change it describes, so the
caller owns the commit and a rolled-back change takes its event with it.

There is no update and no delete here, and none anywhere else - the table also
has triggers refusing both, so the guarantee survives code that forgets.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditEvent, AuditEventType


def record(
    db: Session,
    *,
    service_id: int,
    actor_id: int | None,
    event_type: AuditEventType,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    """Append one event to a service's timeline, without committing."""
    event = AuditEvent(
        service_id=service_id,
        actor_id=actor_id,
        event_type=event_type,
        old_value=old_value,
        new_value=new_value,
        event_metadata=metadata,
    )
    db.add(event)
    return event


def list_for_service(db: Session, service_id: int) -> list[AuditEvent]:
    """The timeline, oldest first - the order it happened in.

    Ordered by id after created_at: two events written in the same transaction
    share a timestamp, and the id is what keeps "assigned" before "status
    changed" instead of letting them shuffle.
    """
    return list(
        db.scalars(
            select(AuditEvent)
            .options(selectinload(AuditEvent.actor))
            .where(AuditEvent.service_id == service_id)
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        ).all()
    )
