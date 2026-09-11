"""Service history export (spec 07, rules 10-14)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.services.export_service import COLUMNS

from .conftest_services import advance_to, assign, make_service, make_vehicle, move

PATH = "/services/export.csv"


def rows(response) -> list[dict]:
    return list(csv.DictReader(io.StringIO(response.text)))


def test_the_export_route_is_not_shadowed_by_the_service_detail_route(
    api: TestClient, manager: dict[str, str]
) -> None:
    """`export.csv` must not be read as a service id.

    FastAPI matches in registration order, so /services/export.csv has to be
    declared before /services/{service_id}. Getting this wrong is a 422 that
    looks like a validation bug.
    """
    response = api.get(PATH, headers=manager)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_a_manager_exports_the_history(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 10."""
    response = api.get(PATH, headers=manager)
    exported = rows(response)

    assert list(exported[0]) == list(COLUMNS)
    assert len(exported) == 1
    assert exported[0]["registration_number"] == "VAN001"
    assert exported[0]["cycle_number"] == "1"
    assert exported[0]["status"] == "due"


def test_a_technician_cannot_export_the_fleet(
    api: TestClient, tech: dict[str, str]
) -> None:
    """Rule 10: a fleet-wide export is not their view."""
    assert api.get(PATH, headers=tech).status_code == 403


def test_the_response_is_a_download(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    disposition = api.get(PATH, headers=manager).headers["content-disposition"]

    assert disposition.startswith("attachment;")
    assert ".csv" in disposition


def test_the_export_is_streamed_not_assembled(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 11.

    Asserted on the generator itself: the export yields the header and each row
    separately, so the whole thing is never one string in memory. A test
    against the response text alone could not tell the two apart.

    The session is opened and closed here rather than borrowed from the app -
    a leaked session holds a transaction open and the fixture's TRUNCATE then
    waits for it forever.
    """
    from sqlalchemy.orm import Session

    from app.services import export_service

    with Session(clean_db) as session:
        chunks = list(
            export_service.stream_csv(
                session, grace_days=7, now=datetime.now(UTC)
            )
        )

    assert len(chunks) >= 2, "the header and the rows should arrive separately"
    assert chunks[0].startswith("registration_number")


def test_filters_narrow_the_export(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    """Rule 12: the same filters as the list, so "export what I see" works."""
    second = make_vehicle(api, manager, registration_number="VAN002")
    other = make_service(api, manager, second["id"], "Tyre change")
    move(api, manager, other["id"], "booked", scheduled_date="2026-10-01")

    by_vehicle = rows(api.get(PATH, params={"vehicle_id": vehicle["id"]}, headers=manager))
    by_status = rows(api.get(PATH, params={"status": "booked"}, headers=manager))
    by_search = rows(api.get(PATH, params={"search": "tyre"}, headers=manager))

    assert [row["registration_number"] for row in by_vehicle] == ["VAN001"]
    assert [row["registration_number"] for row in by_status] == ["VAN002"]
    assert [row["description"] for row in by_search] == ["Tyre change"]


def test_completion_data_is_exported(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 13."""
    advance_to(api, manager, service["id"], "completed", completion_odometer=61_500)

    exported = rows(api.get(PATH, headers=manager))[0]

    assert exported["status"] == "completed"
    assert exported["completion_odometer"] == "61500"
    assert exported["completed_at"].endswith("+00:00"), "ISO-8601 UTC"


def test_an_overdue_record_says_so(
    api: TestClient, manager: dict[str, str], clean_db: Engine, service: dict
) -> None:
    """Rule 13: overdue is derived, so the export computes it."""
    with clean_db.begin() as connection:
        connection.execute(
            text("UPDATE service_records SET due_since = :when WHERE id = :id"),
            {"when": datetime.now(UTC) - timedelta(days=30), "id": service["id"]},
        )

    exported = rows(api.get(PATH, headers=manager))[0]

    assert exported["is_overdue"] == "yes"
    assert exported["status"] == "due", "still stored as due"


def test_several_technicians_share_one_cell(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 13: a spreadsheet user would rather read names than join two files."""
    assign(api, manager, service["id"], people["tech"])
    assign(api, manager, service["id"], people["other_tech"])

    exported = rows(api.get(PATH, headers=manager))[0]

    assert "Sam Okafor" in exported["technicians"]
    assert "Alex Bell" in exported["technicians"]


def test_an_empty_fleet_exports_just_the_header(
    api: TestClient, manager: dict[str, str]
) -> None:
    response = api.get(PATH, headers=manager)

    assert response.status_code == 200
    assert rows(response) == []
    assert response.text.strip().startswith("registration_number")
