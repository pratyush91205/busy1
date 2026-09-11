"""The service lifecycle, as one table and one function.

Due -> Booked -> In Service -> Completed, and nothing else. Keeping the table
here rather than inside a route handler is the whole point: there is one place
to read what is legal, one place for it to be wrong, and adding a status later
does not mean auditing every endpoint that touches status.

Note what is absent: Overdue. It is not a status. It is derived from
status == DUE plus due_since plus the grace period, and putting it here would
give the system two answers to the same question.
"""

from __future__ import annotations

from app.models.enums import ServiceStatus
from app.services.errors import ConflictError

# The only edges in the graph.
ALLOWED_TRANSITIONS: dict[ServiceStatus, frozenset[ServiceStatus]] = {
    ServiceStatus.DUE: frozenset({ServiceStatus.BOOKED}),
    ServiceStatus.BOOKED: frozenset({ServiceStatus.IN_SERVICE}),
    ServiceStatus.IN_SERVICE: frozenset({ServiceStatus.COMPLETED}),
    ServiceStatus.COMPLETED: frozenset(),
}

LABELS = {
    ServiceStatus.DUE: "Due",
    ServiceStatus.BOOKED: "Booked",
    ServiceStatus.IN_SERVICE: "In Service",
    ServiceStatus.COMPLETED: "Completed",
}


def validate_transition(current: str, requested: str) -> None:
    """Raise ConflictError unless ``current -> requested`` is a legal edge.

    The message names both states and what would have been allowed, because
    "invalid transition" on its own tells the caller nothing they can act on.
    """
    current_status = ServiceStatus(current)
    requested_status = ServiceStatus(requested)

    allowed = ALLOWED_TRANSITIONS[current_status]
    if requested_status in allowed:
        return

    if not allowed:
        raise ConflictError(
            f"A {LABELS[current_status]} service cannot change status. "
            "It is the end of the cycle."
        )

    raise ConflictError(
        f"Cannot move a service from {LABELS[current_status]} to "
        f"{LABELS[requested_status]}. "
        f"The only move from {LABELS[current_status]} is to "
        f"{', '.join(LABELS[status] for status in sorted(allowed))}."
    )


def next_statuses(current: str) -> list[ServiceStatus]:
    """What this record could legally become. For the UI, not for a decision."""
    return sorted(ALLOWED_TRANSITIONS[ServiceStatus(current)])
