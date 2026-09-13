"""Overdue records and their alerts (spec 06, rules 5-14).

Records are aged by moving ``due_since`` backwards in the database rather than
by waiting. That is the whole reason the rules take a clock and a grace period
as arguments instead of reading them from the module.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.main import create_app

from .conftest import build_test_settings, client_for
from .conftest_services import advance_to, make_service, make_vehicle, move
from .helpers import auth_header

GRACE = 7


def age(engine: Engine, service_id: int, days: int) -> None:
    """Pretend this record became Due ``days`` ago."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE service_records SET due_since = :when WHERE id = :id"),
            {"when": datetime.now(UTC) - timedelta(days=days), "id": service_id},
        )


def alerts(api: TestClient, headers: dict[str, str]) -> dict:
    response = api.get("/alerts", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def count(api: TestClient, headers: dict[str, str]) -> int:
    return api.get("/alerts/count", headers=headers).json()["count"]


# --- overdue derivation ------------------------------------------------------


def test_due_beyond_the_grace_period_is_overdue(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 5."""
    age(clean_db, service["id"], GRACE + 1)

    read = api.get(f"/services/{service['id']}", headers=manager).json()

    assert read["is_overdue"] is True
    assert read["status"] == "due", "overdue is derived, not a stored status"


def test_due_within_the_grace_period_is_not_overdue(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 5."""
    age(clean_db, service["id"], GRACE - 1)

    assert api.get(f"/services/{service['id']}", headers=manager).json()["is_overdue"] is False


def test_booking_stops_it_being_overdue(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 6: the status is no longer Due, so there is nothing to clear."""
    age(clean_db, service["id"], GRACE + 30)
    assert api.get(f"/services/{service['id']}", headers=manager).json()["is_overdue"]

    advance_to(api, manager, service["id"], "booked")

    assert api.get(f"/services/{service['id']}", headers=manager).json()["is_overdue"] is False


def test_a_completed_record_is_never_overdue(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 8: completion clears due_since."""
    age(clean_db, service["id"], GRACE + 30)
    advance_to(api, manager, service["id"], "completed")

    read = api.get(f"/services/{service['id']}", headers=manager).json()
    assert read["is_overdue"] is False
    assert read["due_since"] is None


def test_overdue_is_not_a_storable_status(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 7: the status enum still holds four values."""
    assert move(api, manager, service["id"], "overdue").status_code == 422
    assert api.get("/services", params={"status": "overdue"}, headers=manager).status_code == 422


def test_the_overdue_filter_selects_in_sql(
    api: TestClient, manager: dict[str, str], clean_db: Engine, vehicle: dict, service: dict
) -> None:
    """Rule 7: a separate filter, not a status value."""
    second = make_vehicle(api, manager, registration_number="VAN002")
    fresh = make_service(api, manager, second["id"], "Fresh")
    age(clean_db, service["id"], GRACE + 2)

    overdue = api.get("/services", params={"overdue": True}, headers=manager).json()
    not_overdue = api.get("/services", params={"overdue": False}, headers=manager).json()

    assert [item["id"] for item in overdue["items"]] == [service["id"]]
    assert overdue["total"] == 1
    assert [item["id"] for item in not_overdue["items"]] == [fresh["id"]]


def test_the_grace_period_comes_from_settings(
    clean_db: Engine, people: dict[str, int]
) -> None:
    """Rule 5, and the reason it is configuration rather than a constant.

    Two apps over the same data, differing only in OVERDUE_GRACE_PERIOD_DAYS,
    must disagree about the same record.
    """
    strict = create_app(build_test_settings(overdue_grace_period_days=1))
    lenient = create_app(build_test_settings(overdue_grace_period_days=30))

    with client_for(strict, clean_db) as strict_client:
        headers = auth_header(strict_client, "manager@fleet.example")
        vehicle = make_vehicle(strict_client, headers)
        service = make_service(strict_client, headers, vehicle["id"])
        age(clean_db, service["id"], 5)

        assert (
            strict_client.get(f"/services/{service['id']}", headers=headers).json()[
                "is_overdue"
            ]
            is True
        )

    with client_for(lenient, clean_db) as lenient_client:
        headers = auth_header(lenient_client, "manager@fleet.example")
        assert (
            lenient_client.get(f"/services/{service['id']}", headers=headers).json()[
                "is_overdue"
            ]
            is False
        )


# --- alerts ------------------------------------------------------------------


def test_an_overdue_record_appears_as_an_alert(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 9: the alert is the record; there is no alert row."""
    age(clean_db, service["id"], GRACE + 3)

    listed = alerts(api, manager)

    assert [item["id"] for item in listed["items"]] == [service["id"]]
    assert count(api, manager) == 1


def test_a_record_within_grace_raises_no_alert(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    assert alerts(api, manager)["total"] == 0
    assert count(api, manager) == 0


def test_dismissing_hides_the_alert_but_not_the_overdue_state(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rules 10 and 11: dismissal acknowledges, it does not service the van."""
    age(clean_db, service["id"], GRACE + 3)

    assert api.post(f"/alerts/{service['id']}/dismiss", headers=manager).status_code == 204

    assert alerts(api, manager)["total"] == 0
    assert count(api, manager) == 0

    still = api.get(f"/services/{service['id']}", headers=manager).json()
    assert still["is_overdue"] is True, "dismissing must not pretend it is serviced"


def test_dismissing_twice_is_refused(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 13."""
    age(clean_db, service["id"], GRACE + 3)
    api.post(f"/alerts/{service['id']}/dismiss", headers=manager)

    second = api.post(f"/alerts/{service['id']}/dismiss", headers=manager)

    assert second.status_code == 409
    assert "already been dismissed" in second.json()["detail"]


def test_dismissing_a_record_that_is_not_overdue_is_refused(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 13: there is no alert to dismiss."""
    response = api.post(f"/alerts/{service['id']}/dismiss", headers=manager)

    assert response.status_code == 409
    assert "not overdue" in response.json()["detail"]


def test_dismissing_an_unknown_record_is_not_found(
    api: TestClient, manager: dict[str, str]
) -> None:
    assert api.post("/alerts/999999/dismiss", headers=manager).status_code == 404


@pytest.mark.parametrize("path", ["/alerts", "/alerts/count"])
def test_a_technician_cannot_see_alerts(
    api: TestClient, tech: dict[str, str], path: str
) -> None:
    """Rule 14: a fleet-wide view is not a technician's."""
    assert api.get(path, headers=tech).status_code == 403


def test_a_technician_cannot_dismiss(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    clean_db: Engine,
    service: dict,
) -> None:
    """Rule 14."""
    age(clean_db, service["id"], GRACE + 3)

    assert api.post(f"/alerts/{service['id']}/dismiss", headers=tech).status_code == 403


def test_a_new_cycle_raises_a_new_alert_without_anything_resetting(
    api: TestClient, manager: dict[str, str], clean_db: Engine, vehicle: dict, service: dict
) -> None:
    """Rule 12 - the requirement this whole design exists to satisfy.

    Dismissal points at a record, and one record is one cycle. The next cycle
    is a different record with no dismissal against it, so its alert appears
    with nothing to clear, expire or reconcile.
    """
    age(clean_db, service["id"], GRACE + 3)
    api.post(f"/alerts/{service['id']}/dismiss", headers=manager)
    assert count(api, manager) == 0

    # Finish this cycle and open the next one.
    advance_to(api, manager, service["id"], "completed")
    assert count(api, manager) == 0

    second = make_service(api, manager, vehicle["id"], "Next cycle")
    assert second["cycle_number"] == 2
    assert count(api, manager) == 0, "a fresh cycle is inside its grace period"

    age(clean_db, second["id"], GRACE + 1)

    assert count(api, manager) == 1
    assert [item["id"] for item in alerts(api, manager)["items"]] == [second["id"]]


def test_alerts_are_ordered_longest_overdue_first(
    api: TestClient, manager: dict[str, str], clean_db: Engine, vehicle: dict, service: dict
) -> None:
    second_vehicle = make_vehicle(api, manager, registration_number="VAN002")
    second = make_service(api, manager, second_vehicle["id"], "Other")

    age(clean_db, service["id"], GRACE + 2)
    age(clean_db, second["id"], GRACE + 20)

    listed = alerts(api, manager)

    assert [item["id"] for item in listed["items"]] == [second["id"], service["id"]]
