"""Dashboard aggregates (spec 08).

Every assertion builds a known world and checks the number, rather than
checking the shape of the response. A dashboard that returns plausible numbers
is worse than one that returns none.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.services.dashboard_service import WEEKS, week_start

from .conftest_services import advance_to, assign, make_service, make_vehicle, move


def dashboard(api: TestClient, headers: dict[str, str]) -> dict:
    response = api.get("/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def age_due_since(engine: Engine, service_id: int, days: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE service_records SET due_since = :when WHERE id = :id"),
            {"when": datetime.now(UTC) - timedelta(days=days), "id": service_id},
        )


def backdate_completion(engine: Engine, service_id: int, days: int) -> None:
    """Move a completion into the past - the one thing the rules cannot do."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE service_records SET completed_at = :when WHERE id = :id"),
            {"when": datetime.now(UTC) - timedelta(days=days), "id": service_id},
        )


# --- authorization -----------------------------------------------------------


def test_a_technician_cannot_read_the_dashboard(
    api: TestClient, tech: dict[str, str]
) -> None:
    """Rule 1: a fleet-wide summary is not their view."""
    assert api.get("/dashboard", headers=tech).status_code == 403


# --- counts ------------------------------------------------------------------


def test_an_empty_fleet_reports_zeros_not_omissions(
    api: TestClient, manager: dict[str, str], people: dict[str, int]
) -> None:
    """Rules 5, 6, 7: a missing bucket is not the same as a zero."""
    body = dashboard(api, manager)

    assert body["vehicles"] == {"total": 0, "due": 0, "in_service": 0, "archived": 0}
    assert [row["status"] for row in body["by_status"]] == [
        "due",
        "booked",
        "in_service",
        "completed",
    ]
    assert all(row["count"] == 0 for row in body["by_status"])
    assert len(body["completed_per_week"]) == WEEKS
    # Every technician appears, even with nothing assigned.
    assert len(body["by_technician"]) == 2


def test_vehicle_counts_exclude_archived(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 3."""
    make_vehicle(api, manager, registration_number="LIVE01")
    archived = make_vehicle(api, manager, registration_number="GONE01")
    api.post(f"/vehicles/{archived['id']}/archive", headers=manager)

    body = dashboard(api, manager)

    assert body["vehicles"]["total"] == 1
    assert body["vehicles"]["archived"] == 1


def test_the_due_count_matches_the_due_filter(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 3: the tile and the list must not disagree."""
    due = make_vehicle(api, manager, registration_number="DUE001")
    api.patch(
        f"/vehicles/{due['id']}", json={"current_odometer": 61_000}, headers=manager
    )
    make_vehicle(api, manager, registration_number="FINE01")

    body = dashboard(api, manager)
    listed = api.get("/vehicles", params={"due": True}, headers=manager).json()

    assert body["vehicles"]["due"] == 1
    assert body["vehicles"]["due"] == listed["total"]


def test_in_service_counts_vehicles_not_records(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    move(api, manager, service["id"], "booked", scheduled_date="2026-10-01")
    move(api, manager, service["id"], "in_service")

    body = dashboard(api, manager)

    assert body["vehicles"]["in_service"] == 1
    assert body["by_status"][2] == {"status": "in_service", "count": 1}


def test_the_overdue_count_agrees_with_the_alert_badge(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 3, the one that matters.

    The dashboard tile and the nav badge are two queries over one idea. If they
    ever disagree the manager has no way to tell which is lying, so they are
    asserted equal rather than each asserted correct.
    """
    age_due_since(clean_db, service["id"], 30)

    body = dashboard(api, manager)
    badge = api.get("/alerts/count", headers=manager).json()["count"]

    assert body["services"]["overdue"] == 1
    assert body["services"]["overdue"] == badge


def test_a_dismissed_alert_leaves_the_overdue_count(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 3: dismissal hides the alert, and the tile follows it."""
    age_due_since(clean_db, service["id"], 30)
    api.post(f"/alerts/{service['id']}/dismiss", headers=manager)

    body = dashboard(api, manager)

    assert body["services"]["overdue"] == 0
    assert body["services"]["overdue"] == api.get(
        "/alerts/count", headers=manager
    ).json()["count"]


def test_completed_this_week_counts_the_current_iso_week(
    api: TestClient, manager: dict[str, str], clean_db: Engine, vehicle: dict, service: dict
) -> None:
    """Rule 4."""
    advance_to(api, manager, service["id"], "completed")

    assert dashboard(api, manager)["services"]["completed_this_week"] == 1

    # Push it back beyond the current week's Monday.
    days_since_monday = datetime.now(UTC).weekday()
    backdate_completion(clean_db, service["id"], days_since_monday + 1)

    assert dashboard(api, manager)["services"]["completed_this_week"] == 0


def test_open_services_excludes_completed_ones(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    assert dashboard(api, manager)["services"]["open"] == 1

    advance_to(api, manager, service["id"], "completed")

    assert dashboard(api, manager)["services"]["open"] == 0


# --- technician workload -----------------------------------------------------


def test_technician_workload_includes_the_idle_one(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 7: an idle technician should be visible, not absent."""
    assign(api, manager, service["id"], people["tech"])

    rows = {row["full_name"]: row for row in dashboard(api, manager)["by_technician"]}

    assert rows["Sam Okafor"]["open"] == 1
    assert rows["Sam Okafor"]["completed"] == 0
    assert rows["Alex Bell"]["open"] == 0, "the idle technician must still appear"


def test_technician_workload_separates_open_from_completed(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    assign(api, manager, service["id"], people["tech"])
    advance_to(api, manager, service["id"], "completed")

    rows = {row["full_name"]: row for row in dashboard(api, manager)["by_technician"]}

    assert rows["Sam Okafor"]["open"] == 0
    assert rows["Sam Okafor"]["completed"] == 1


def test_a_manager_is_not_listed_as_a_technician(
    api: TestClient, manager: dict[str, str], people: dict[str, int]
) -> None:
    names = {row["full_name"] for row in dashboard(api, manager)["by_technician"]}

    assert "Morgan Reed" not in names


# --- the eight-week series ---------------------------------------------------


def test_the_series_has_eight_buckets_oldest_first(
    api: TestClient, manager: dict[str, str], people: dict[str, int]
) -> None:
    """Rule 5."""
    series = dashboard(api, manager)["completed_per_week"]

    assert len(series) == WEEKS
    starts = [date.fromisoformat(row["week_start"]) for row in series]
    assert starts == sorted(starts)
    # The current week is the eighth bucket, not a ninth.
    assert starts[-1] == week_start(datetime.now(UTC))
    # Every bucket is a Monday.
    assert all(start.weekday() == 0 for start in starts)


def test_quiet_weeks_are_zeros_not_gaps(
    api: TestClient, manager: dict[str, str], clean_db: Engine, vehicle: dict, service: dict
) -> None:
    """Rule 5: a chart that drops empty weeks says the fleet was always busy."""
    advance_to(api, manager, service["id"], "completed")
    backdate_completion(clean_db, service["id"], 21)

    series = dashboard(api, manager)["completed_per_week"]

    assert len(series) == WEEKS
    assert sum(row["count"] for row in series) == 1
    assert sum(1 for row in series if row["count"] == 0) == WEEKS - 1


def test_a_completion_older_than_the_window_is_excluded(
    api: TestClient, manager: dict[str, str], clean_db: Engine, vehicle: dict, service: dict
) -> None:
    advance_to(api, manager, service["id"], "completed")
    backdate_completion(clean_db, service["id"], 120)

    series = dashboard(api, manager)["completed_per_week"]

    assert sum(row["count"] for row in series) == 0
    # But it is still counted as a completed record overall.
    assert dashboard(api, manager)["by_status"][3]["count"] == 1
