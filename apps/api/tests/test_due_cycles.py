"""Vehicles that fall due open their own service cycle.

Goal 4 says a vehicle becomes due when an interval is reached, and that a record
left Due past the grace period is overdue. Goal 10 says that when the vehicle
falls due again and is again left unbooked, the alert returns. Both depend on a
Due record existing without a manager having to notice and open one - so no
test here opens a record by hand.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from .conftest_services import advance_to, make_vehicle

GRACE = 7


def due_records(api: TestClient, headers: dict[str, str], vehicle_id: int) -> list[dict]:
    return api.get(
        "/services",
        params={"vehicle_id": vehicle_id, "status": "due"},
        headers=headers,
    ).json()["items"]


def start_cycle_days_ago(engine: Engine, vehicle_id: int, days: int) -> None:
    """Pretend the vehicle's current cycle began ``days`` ago."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE vehicles SET service_baseline_date = :day WHERE id = :id"),
            {"day": (datetime.now(UTC) - timedelta(days=days)).date(), "id": vehicle_id},
        )


def alert_count(api: TestClient, headers: dict[str, str]) -> int:
    return api.get("/alerts/count", headers=headers).json()["count"]


# --- mileage: opened by the write that crossed ------------------------------


def test_driving_past_the_mileage_interval_opens_a_due_record(
    api: TestClient, manager: dict[str, str]
) -> None:
    vehicle = make_vehicle(api, manager, current_odometer=50_000)

    response = api.patch(
        f"/vehicles/{vehicle['id']}", json={"current_odometer": 60_000}, headers=manager
    )

    assert response.status_code == 200, response.text
    assert response.json()["service_status"]["has_open_record"] is True
    [record] = due_records(api, manager, vehicle["id"])
    assert record["cycle_number"] == 1
    assert "mileage" in record["description"].lower()
    assert record["is_overdue"] is False


def test_the_timeline_says_the_system_opened_it(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Nobody opened it, so no person is named as having done so."""
    vehicle = make_vehicle(api, manager)
    api.patch(
        f"/vehicles/{vehicle['id']}", json={"current_odometer": 60_000}, headers=manager
    )
    [record] = due_records(api, manager, vehicle["id"])

    timeline = api.get(f"/services/{record['id']}/timeline", headers=manager).json()

    assert timeline[0]["event_type"] == "service_created"
    assert timeline[0]["actor"] is None


def test_a_bulk_reading_that_crosses_the_interval_says_so(
    api: TestClient, manager: dict[str, str]
) -> None:
    make_vehicle(api, manager, registration_number="VAN001", current_odometer=50_000)
    make_vehicle(api, manager, registration_number="VAN002", current_odometer=50_000)
    content = "registration_number,odometer\nVAN001,60500\nVAN002,51000\n"

    response = api.post(
        "/vehicles/odometer-upload",
        files={"file": ("readings.csv", content, "text/csv")},
        headers=manager,
    )

    crossed, short = response.json()["results"]
    assert "now due" in crossed["message"].lower()
    assert "now due" not in short["message"].lower()


# --- date: opened on read, dated when it landed ------------------------------


def test_a_date_interval_that_landed_opens_a_record_dated_that_day(
    api: TestClient, manager: dict[str, str], clean_db: Engine
) -> None:
    """The overdue clock starts when the vehicle fell due, not when someone looked."""
    vehicle = make_vehicle(api, manager, service_date_interval=30)
    start_cycle_days_ago(clean_db, vehicle["id"], days=40)  # fell due ten days ago

    [record] = due_records(api, manager, vehicle["id"])

    landed = (datetime.now(UTC) - timedelta(days=10)).date()
    assert datetime.fromisoformat(record["due_since"]) == datetime.combine(
        landed, time.min, tzinfo=UTC
    )
    # Ten days Due against seven of grace: overdue on arrival, because it is.
    assert record["is_overdue"] is True


def test_reading_again_opens_nothing_more(
    api: TestClient, manager: dict[str, str], clean_db: Engine
) -> None:
    vehicle = make_vehicle(api, manager, service_date_interval=30)
    start_cycle_days_ago(clean_db, vehicle["id"], days=31)

    for _ in range(3):
        api.get("/services", headers=manager)
        api.get("/alerts/count", headers=manager)
        api.get("/dashboard", headers=manager)

    listed = api.get(
        "/services", params={"vehicle_id": vehicle["id"]}, headers=manager
    ).json()
    assert listed["total"] == 1


def test_an_archived_vehicle_opens_nothing(
    api: TestClient, manager: dict[str, str], clean_db: Engine
) -> None:
    vehicle = make_vehicle(api, manager, service_date_interval=30)
    api.post(f"/vehicles/{vehicle['id']}/archive", headers=manager)
    start_cycle_days_ago(clean_db, vehicle["id"], days=60)

    listed = api.get(
        "/services", params={"vehicle_id": vehicle["id"]}, headers=manager
    ).json()

    assert listed["total"] == 0


# --- goal 10, end to end -----------------------------------------------------


def test_the_alert_returns_when_the_vehicle_falls_due_again(
    api: TestClient, manager: dict[str, str], clean_db: Engine
) -> None:
    """Dismiss, service, fall due again, sit unbooked: the alert is back.

    At no point does anyone open a record by hand.
    """
    vehicle = make_vehicle(api, manager, service_date_interval=30)
    start_cycle_days_ago(clean_db, vehicle["id"], days=30 + GRACE + 2)

    assert alert_count(api, manager) == 1
    [first] = due_records(api, manager, vehicle["id"])
    assert api.post(f"/alerts/{first['id']}/dismiss", headers=manager).status_code == 204
    assert alert_count(api, manager) == 0

    advance_to(api, manager, first["id"], "completed", completion_odometer=50_000)
    assert alert_count(api, manager) == 0, "a freshly serviced vehicle is not due"

    # The next cycle's date interval lands and the vehicle is left unbooked.
    start_cycle_days_ago(clean_db, vehicle["id"], days=30 + GRACE + 1)

    assert alert_count(api, manager) == 1
    [second] = due_records(api, manager, vehicle["id"])
    assert second["cycle_number"] == 2
    assert second["id"] != first["id"]
