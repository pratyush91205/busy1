"""Vehicle due calculation (spec 06, rules 1-4).

Driven through the rule function with a clock passed in, so a vehicle can be
aged six months without sleeping, and through the API for the filter.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models import Vehicle
from app.services.maintenance import DueReason, vehicle_service_status

from .conftest_services import make_service, make_vehicle, advance_to

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def vehicle(
    *,
    baseline_date: date = date(2026, 9, 1),
    baseline_odometer: int = 50_000,
    current_odometer: int = 50_000,
    date_interval: int = 180,
    mileage_interval: int = 10_000,
    archived: bool = False,
) -> Vehicle:
    return Vehicle(
        registration_number="VAN001",
        make="Ford",
        model="Transit",
        current_odometer=current_odometer,
        service_baseline_odometer=baseline_odometer,
        service_baseline_date=baseline_date,
        service_date_interval=date_interval,
        service_mileage_interval=mileage_interval,
        is_archived=archived,
    )


def test_neither_interval_reached_is_not_due() -> None:
    status = vehicle_service_status(vehicle(), has_open_record=False, now=NOW)

    assert status.is_due is False
    assert status.reason is None


def test_the_date_interval_alone_makes_it_due() -> None:
    """Rule 1: either condition, not both."""
    status = vehicle_service_status(
        vehicle(baseline_date=NOW.date() - timedelta(days=180)),
        has_open_record=False,
        now=NOW,
    )

    assert status.is_due is True
    assert status.reason is DueReason.DATE


def test_the_mileage_interval_alone_makes_it_due() -> None:
    """Rule 1."""
    status = vehicle_service_status(
        vehicle(current_odometer=60_000), has_open_record=False, now=NOW
    )

    assert status.is_due is True
    assert status.reason is DueReason.MILEAGE


def test_both_reached_reports_both() -> None:
    status = vehicle_service_status(
        vehicle(
            baseline_date=NOW.date() - timedelta(days=200), current_odometer=61_000
        ),
        has_open_record=False,
        now=NOW,
    )

    assert status.reason is DueReason.BOTH


def test_the_day_the_interval_lands_is_due() -> None:
    """`>=`, not `>`: on day 180 of a 180-day interval it is due."""
    exactly = vehicle(baseline_date=NOW.date() - timedelta(days=180))
    day_before = vehicle(baseline_date=NOW.date() - timedelta(days=179))

    assert vehicle_service_status(exactly, False, NOW).is_due is True
    assert vehicle_service_status(day_before, False, NOW).is_due is False


def test_the_mile_the_interval_lands_is_due() -> None:
    on_it = vehicle(current_odometer=60_000)
    one_short = vehicle(current_odometer=59_999)

    assert vehicle_service_status(on_it, False, NOW).is_due is True
    assert vehicle_service_status(one_short, False, NOW).is_due is False


def test_an_archived_vehicle_is_never_due() -> None:
    """Rule 3: it is not in service."""
    status = vehicle_service_status(
        vehicle(
            archived=True,
            baseline_date=NOW.date() - timedelta(days=400),
            current_odometer=90_000,
        ),
        has_open_record=False,
        now=NOW,
    )

    assert status.is_due is False


def test_the_next_due_point_is_reported_not_just_the_answer() -> None:
    """Rule 4: a manager needs to see what it is measured against."""
    status = vehicle_service_status(vehicle(), has_open_record=False, now=NOW)

    assert status.next_due_date == date(2026, 9, 1) + timedelta(days=180)
    assert status.next_due_odometer == 60_000


# --- through the API ---------------------------------------------------------


def test_a_new_vehicle_is_not_instantly_due(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 2: a used van joining the fleet with mileage on it is not due."""
    created = make_vehicle(api, manager, current_odometer=80_000)

    assert created["service_status"]["is_due"] is False
    assert created["service_status"]["next_due_odometer"] == 90_000


def test_driving_past_the_mileage_interval_makes_it_due(
    api: TestClient, manager: dict[str, str]
) -> None:
    created = make_vehicle(api, manager, current_odometer=50_000)

    api.patch(
        f"/vehicles/{created['id']}",
        json={"current_odometer": 60_500},
        headers=manager,
    )
    read = api.get(f"/vehicles/{created['id']}", headers=manager).json()

    assert read["service_status"]["is_due"] is True
    assert read["service_status"]["reason"] == "mileage"


def test_completing_a_service_resets_both_counters(
    api: TestClient, manager: dict[str, str]
) -> None:
    """The reset the brief asks for: the next cycle counts from the completion."""
    created = make_vehicle(api, manager, current_odometer=50_000)
    api.patch(
        f"/vehicles/{created['id']}", json={"current_odometer": 61_000}, headers=manager
    )

    due_now = api.get(f"/vehicles/{created['id']}", headers=manager).json()
    assert due_now["service_status"]["is_due"] is True

    # Driving past the interval opened the cycle; nobody opens it by hand.
    service = api.get(
        "/services", params={"vehicle_id": created["id"]}, headers=manager
    ).json()["items"][0]
    advance_to(api, manager, service["id"], "completed", completion_odometer=61_000)

    after = api.get(f"/vehicles/{created['id']}", headers=manager).json()
    assert after["service_status"]["is_due"] is False
    assert after["service_baseline_odometer"] == 61_000
    assert after["service_status"]["next_due_odometer"] == 71_000


def test_the_due_filter_selects_in_sql(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Filtered server-side, so `total` describes the filtered set."""
    due = make_vehicle(api, manager, registration_number="DUE001")
    api.patch(f"/vehicles/{due['id']}", json={"current_odometer": 61_000}, headers=manager)
    make_vehicle(api, manager, registration_number="FINE01")

    listed = api.get("/vehicles", params={"due": True}, headers=manager).json()

    assert listed["total"] == 1
    assert [v["registration_number"] for v in listed["items"]] == ["DUE001"]

    not_due = api.get("/vehicles", params={"due": False}, headers=manager).json()
    assert [v["registration_number"] for v in not_due["items"]] == ["FINE01"]


def test_the_due_filter_agrees_with_the_rule_function(
    api: TestClient, manager: dict[str, str]
) -> None:
    """The SQL predicate and the Python rule must not drift apart.

    They are two implementations of one rule - the filter has to run in the
    database for paging to be honest, and the per-row answer has to be computed
    for the detail view - so this asserts they agree.
    """
    for index, odometer in enumerate([50_000, 59_999, 60_000, 75_000]):
        created = make_vehicle(api, manager, registration_number=f"MIX{index:03d}")
        if odometer > 50_000:
            api.patch(
                f"/vehicles/{created['id']}",
                json={"current_odometer": odometer},
                headers=manager,
            )

    every = api.get("/vehicles", params={"limit": 100}, headers=manager).json()
    by_filter = api.get(
        "/vehicles", params={"due": True, "limit": 100}, headers=manager
    ).json()

    computed = {v["id"] for v in every["items"] if v["service_status"]["is_due"]}
    filtered = {v["id"] for v in by_filter["items"]}

    assert computed == filtered


def test_a_vehicle_reports_whether_it_already_has_an_open_record(
    api: TestClient, manager: dict[str, str]
) -> None:
    """So the UI can say "due, and a record is open" rather than nagging."""
    created = make_vehicle(api, manager)

    before = api.get(f"/vehicles/{created['id']}", headers=manager).json()
    assert before["service_status"]["has_open_record"] is False

    make_service(api, manager, created["id"])

    after = api.get(f"/vehicles/{created['id']}", headers=manager).json()
    assert after["service_status"]["has_open_record"] is True
