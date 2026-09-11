"""Domain enumerations.

Stored as VARCHAR with a CHECK constraint rather than a native PostgreSQL enum
type: adding a value later is a one-line migration instead of an ALTER TYPE,
and the values stay readable in a psql session.
"""

from collections.abc import Iterable
from enum import StrEnum


class UserRole(StrEnum):
    FLEET_MANAGER = "fleet_manager"
    TECHNICIAN = "technician"


class ServiceStatus(StrEnum):
    """The four stored lifecycle states.

    Overdue is NOT here and must never be added: it is derived from
    status == DUE plus due_since plus the grace period. Adding it would give
    the system two places to disagree about whether a service is overdue.
    """

    DUE = "due"
    BOOKED = "booked"
    IN_SERVICE = "in_service"
    COMPLETED = "completed"


class AuditEventType(StrEnum):
    SERVICE_CREATED = "service_created"
    STATUS_CHANGED = "status_changed"
    TECHNICIAN_ASSIGNED = "technician_assigned"
    TECHNICIAN_UNASSIGNED = "technician_unassigned"
    NOTE_ADDED = "note_added"


def sql_in(column: str, values: Iterable[str]) -> str:
    """Render `column IN ('a', 'b')` for a CHECK constraint."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"
