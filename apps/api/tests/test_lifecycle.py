"""Service lifecycle rules (spec 05, rules 7 to 11).

The transition table is tested exhaustively rather than by example: every
ordered pair of the four statuses is either on the legal list or must be
refused. A test that only checks the three happy paths would pass just as well
against a service layer that allowed everything.
"""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.models.enums import ServiceStatus

from .conftest_services import advance_to, assign, move

STATUSES = [status.value for status in ServiceStatus]

LEGAL = {("due", "booked"), ("booked", "in_service"), ("in_service", "completed")}

EXTRA_FOR = {
    "booked": {"scheduled_date": "2026-10-01"},
    "completed": {"completion_odometer": 60_000},
}


@pytest.mark.parametrize(("start", "target"), sorted(LEGAL))
def test_every_legal_transition_is_allowed(
    api: TestClient, manager: dict[str, str], service: dict, start: str, target: str
) -> None:
    """Rule 7, the three edges that exist."""
    if start != "due":
        advance_to(api, manager, service["id"], start)

    response = move(api, manager, service["id"], target, **EXTRA_FOR.get(target, {}))

    assert response.status_code == 200, response.text
    assert response.json()["status"] == target


@pytest.mark.parametrize(
    ("start", "target"),
    [pair for pair in itertools.product(STATUSES, STATUSES) if pair not in LEGAL],
)
def test_every_other_transition_is_refused(
    api: TestClient, manager: dict[str, str], service: dict, start: str, target: str
) -> None:
    """Rule 7, the thirteen edges that do not - including each status to itself."""
    if start != "due":
        advance_to(api, manager, service["id"], start)

    response = move(api, manager, service["id"], target, **EXTRA_FOR.get(target, {}))

    assert response.status_code == 409, f"{start} -> {target} was allowed"
    # The message has to name both states, or the client learns nothing.
    detail = response.json()["detail"].lower()
    assert start.replace("_", " ") in detail


def test_an_unknown_status_is_unprocessable(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """`overdue` is not a status and must not become one."""
    response = move(api, manager, service["id"], "overdue")

    assert response.status_code == 422


def test_booking_without_a_date_is_refused(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 8."""
    response = move(api, manager, service["id"], "booked")

    assert response.status_code == 409
    assert "scheduled date" in response.json()["detail"].lower()


def test_booking_records_the_scheduled_date(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    response = move(
        api, manager, service["id"], "booked", scheduled_date="2026-10-01"
    )

    assert response.json()["scheduled_date"] == "2026-10-01"


# --- completion --------------------------------------------------------------


def test_completing_without_an_odometer_is_refused(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 9."""
    advance_to(api, manager, service["id"], "in_service")

    response = move(api, manager, service["id"], "completed")

    assert response.status_code == 409
    assert "odometer" in response.json()["detail"].lower()


def test_a_completion_odometer_below_the_vehicles_is_refused(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 9: a vehicle cannot have travelled backwards between services."""
    advance_to(api, manager, service["id"], "in_service")

    response = move(
        api, manager, service["id"], "completed", completion_odometer=49_000
    )

    assert response.status_code == 409
    assert "49000" in response.json()["detail"]


def test_completing_closes_the_cycle_and_moves_the_vehicle(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    """Rule 10, the whole transaction."""
    advance_to(api, manager, service["id"], "in_service")

    completed = move(
        api, manager, service["id"], "completed", completion_odometer=61_500
    ).json()

    assert completed["status"] == "completed"
    assert completed["completion_odometer"] == 61_500
    assert completed["completed_at"] is not None
    # The cycle is over, so it is no longer due - and so cannot read as overdue.
    assert completed["due_since"] is None

    moved = api.get(f"/vehicles/{vehicle['id']}", headers=manager).json()
    assert moved["current_odometer"] == 61_500


def test_a_refused_completion_changes_nothing(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    """Rule 10: the vehicle must not move when the completion is rejected."""
    advance_to(api, manager, service["id"], "in_service")

    move(api, manager, service["id"], "completed", completion_odometer=10)

    unchanged = api.get(f"/services/{service['id']}", headers=manager).json()
    assert unchanged["status"] == "in_service"
    assert unchanged["completed_at"] is None

    vehicle_now = api.get(f"/vehicles/{vehicle['id']}", headers=manager).json()
    assert vehicle_now["current_odometer"] == 50_000


def test_a_failing_audit_insert_rolls_the_status_change_back(
    api: TestClient,
    manager: dict[str, str],
    clean_db: Engine,
    service: dict,
) -> None:
    """Rule 10, the part worth proving rather than asserting in a comment.

    The audit event and the change it describes share one transaction. Break
    the audit insert and the status change must go with it - a service that
    completed with no record of completing is exactly what the audit trail
    exists to make impossible.
    """
    advance_to(api, manager, service["id"], "in_service")

    # A trigger that refuses the insert, standing in for any failure on the
    # audit write. Nothing in the application knows it is there.
    with clean_db.begin() as connection:
        connection.execute(
            text(
                """
                CREATE FUNCTION refuse_audit() RETURNS trigger AS $$
                BEGIN RAISE EXCEPTION 'audit write failed'; END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER refuse_audit_insert BEFORE INSERT ON audit_events
                FOR EACH ROW EXECUTE FUNCTION refuse_audit();
                """
            )
        )

    try:
        response = move(
            api, manager, service["id"], "completed", completion_odometer=61_500
        )
        assert response.status_code == 503, response.text
    finally:
        with clean_db.begin() as connection:
            connection.execute(
                text("DROP TRIGGER refuse_audit_insert ON audit_events")
            )
            connection.execute(text("DROP FUNCTION refuse_audit()"))

    still_in_service = api.get(f"/services/{service['id']}", headers=manager).json()
    assert still_in_service["status"] == "in_service"
    assert still_in_service["completed_at"] is None


# --- who may move what -------------------------------------------------------


def test_an_assigned_technician_may_start_and_complete(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 11: the work a technician actually does."""
    assign(api, manager, service["id"], people["tech"])
    move(api, manager, service["id"], "booked", scheduled_date="2026-10-01")

    started = move(api, tech, service["id"], "in_service")
    assert started.status_code == 200, started.text

    completed = move(api, tech, service["id"], "completed", completion_odometer=60_000)
    assert completed.status_code == 200, completed.text


def test_a_technician_may_not_book(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 11: booking sets the schedule, which is a manager's call."""
    assign(api, manager, service["id"], people["tech"])

    response = move(api, tech, service["id"], "booked", scheduled_date="2026-10-01")

    assert response.status_code == 403
    assert "fleet manager" in response.json()["detail"].lower()


def test_an_unassigned_technician_cannot_move_a_record(
    api: TestClient,
    manager: dict[str, str],
    other_tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    assign(api, manager, service["id"], people["tech"])
    move(api, manager, service["id"], "booked", scheduled_date="2026-10-01")

    response = move(api, other_tech, service["id"], "in_service")

    # 404, not 403: an unassigned technician is not told the record exists.
    assert response.status_code == 404
