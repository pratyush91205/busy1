"""Bulk odometer upload (spec 07, rules 1-9).

The rule that matters is 4: valid rows are applied even when other rows fail.
It is asserted against the database rather than against the response, because
a response can claim anything.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from .conftest_services import make_vehicle

HEADER = "registration_number,odometer"


def upload(api: TestClient, headers: dict[str, str], body: str):
    return api.post(
        "/vehicles/odometer-upload",
        files={"file": ("readings.csv", body.encode(), "text/csv")},
        headers=headers,
    )


def odometer(api: TestClient, headers: dict[str, str], vehicle_id: int) -> int:
    return api.get(f"/vehicles/{vehicle_id}", headers=headers).json()[
        "current_odometer"
    ]


@pytest.fixture
def fleet(api: TestClient, manager: dict[str, str]) -> dict[str, dict]:
    return {
        "VAN001": make_vehicle(
            api, manager, registration_number="VAN001", current_odometer=51_000
        ),
        "VAN002": make_vehicle(
            api, manager, registration_number="VAN002", current_odometer=76_500
        ),
        "VAN003": make_vehicle(
            api, manager, registration_number="VAN003", current_odometer=45_000
        ),
    }


# --- the whole-file rules ----------------------------------------------------


def test_a_manager_uploads_readings(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 1."""
    response = upload(api, manager, f"{HEADER}\nVAN001,52300\nVAN003,46000\n")

    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["succeeded"], body["failed"]) == (2, 2, 0)
    assert odometer(api, manager, fleet["VAN001"]["id"]) == 52_300


def test_a_technician_cannot_upload(
    api: TestClient, tech: dict[str, str], fleet: dict
) -> None:
    """Rule 1."""
    assert upload(api, tech, f"{HEADER}\nVAN001,52300\n").status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        "vehicle_id,odometer\n1,100\n",
        "registration_number\nVAN001\n",
        "odometer,registration_number\n100,VAN001\n",
        "",
    ],
)
def test_a_wrong_header_rejects_the_whole_file(
    api: TestClient, manager: dict[str, str], fleet: dict, body: str
) -> None:
    """Rule 2: the file is not the thing this endpoint takes."""
    response = upload(api, manager, body)

    assert response.status_code == 422
    assert "registration_number,odometer" in response.json()["detail"]


def test_a_rejected_header_writes_nothing(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 2: no row in an unreadable file may be trusted."""
    upload(api, manager, "wrong,header\nVAN001,99999\n")

    assert odometer(api, manager, fleet["VAN001"]["id"]) == 51_000


# --- the rule this endpoint exists for ---------------------------------------


def test_valid_rows_are_applied_even_when_others_fail(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 4 - the central one.

    Checked against the database, not the response. A depot upload where one
    row is a typo must not discard the other two.
    """
    response = upload(
        api,
        manager,
        f"{HEADER}\n"
        "VAN001,52300\n"      # fine
        "VAN002,76000\n"      # lower than 76,500 - rejected
        "VAN003,46000\n",     # fine, and after the failure
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["succeeded"], body["failed"]) == (2, 1)

    assert odometer(api, manager, fleet["VAN001"]["id"]) == 52_300
    assert odometer(api, manager, fleet["VAN002"]["id"]) == 76_500, "unchanged"
    assert odometer(api, manager, fleet["VAN003"]["id"]) == 46_000, (
        "a row after a failure must still be applied"
    )


# --- per-row rejections ------------------------------------------------------


def test_a_lower_reading_is_rejected_with_both_numbers(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 5."""
    body = upload(api, manager, f"{HEADER}\nVAN002,76000\n").json()

    rejected = body["results"][0]
    assert rejected["status"] == "rejected"
    assert "76000" in rejected["message"] and "76500" in rejected["message"]


def test_an_equal_reading_is_an_accepted_no_op(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 6: re-sending today's reading is not an error."""
    body = upload(api, manager, f"{HEADER}\nVAN001,51000\n").json()

    assert body["succeeded"] == 1
    assert "nothing to change" in body["results"][0]["message"].lower()
    assert odometer(api, manager, fleet["VAN001"]["id"]) == 51_000


def test_an_unknown_registration_is_rejected(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 5."""
    body = upload(api, manager, f"{HEADER}\nNOPE99,1000\n").json()

    assert body["failed"] == 1
    assert "NOPE99" in body["results"][0]["message"]


@pytest.mark.parametrize("value", ["-1", "abc", "", "12.5"])
def test_a_bad_odometer_value_is_rejected(
    api: TestClient, manager: dict[str, str], fleet: dict, value: str
) -> None:
    """Rule 5."""
    body = upload(api, manager, f"{HEADER}\nVAN001,{value}\n").json()

    assert body["failed"] == 1
    assert body["results"][0]["status"] == "rejected"


def test_an_archived_vehicle_is_rejected(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 5, and why archived vehicles refuse edits at all (decision 12)."""
    api.post(f"/vehicles/{fleet['VAN001']['id']}/archive", headers=manager)

    body = upload(api, manager, f"{HEADER}\nVAN001,52300\n").json()

    assert body["failed"] == 1
    assert "archived" in body["results"][0]["message"].lower()
    assert odometer(api, manager, fleet["VAN001"]["id"]) == 51_000


def test_a_repeated_registration_rejects_the_second_row(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 5: two readings for one van in one file is a mistake worth saying."""
    body = upload(api, manager, f"{HEADER}\nVAN001,52000\nVAN001,53000\n").json()

    assert (body["succeeded"], body["failed"]) == (1, 1)
    assert "row 1" in body["results"][1]["message"]
    assert odometer(api, manager, fleet["VAN001"]["id"]) == 52_000


# --- parsing -----------------------------------------------------------------


def test_blank_lines_are_skipped(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 9: a trailing newline is not a failed row."""
    body = upload(api, manager, f"{HEADER}\nVAN001,52300\n\n\n").json()

    assert body["total"] == 1
    assert body["failed"] == 0


def test_row_numbers_count_data_rows_not_the_header(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """What a person looking at their spreadsheet counts."""
    body = upload(api, manager, f"{HEADER}\nVAN001,52300\nNOPE,1\n").json()

    assert [result["row"] for result in body["results"]] == [1, 2]


def test_registrations_are_matched_after_normalising(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """The CSV and the API must agree on what a registration is."""
    body = upload(api, manager, f"{HEADER}\n  van001 ,52300\n").json()

    assert body["succeeded"] == 1
    assert odometer(api, manager, fleet["VAN001"]["id"]) == 52_300


def test_a_byte_order_mark_does_not_break_the_header(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Excel writes one. Rejecting it would look like a malformed header."""
    response = upload(api, manager, f"﻿{HEADER}\nVAN001,52300\n")

    assert response.status_code == 200
    assert response.json()["succeeded"] == 1


def test_a_file_over_the_row_cap_is_refused(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 8: an uncapped upload is a way to take the process down."""
    rows = "\n".join(f"VAN{index:04d},1000" for index in range(5_001))

    response = upload(api, manager, f"{HEADER}\n{rows}\n")

    assert response.status_code == 422
    assert "5000" in response.json()["detail"]


def test_a_reading_does_not_reset_the_service_baseline(
    api: TestClient, manager: dict[str, str], fleet: dict
) -> None:
    """Rule 7: a reading is not a service.

    If an upload moved the baseline, driving a van would push its next service
    further away instead of bringing it closer - the opposite of the point.
    """
    before = api.get(f"/vehicles/{fleet['VAN001']['id']}", headers=manager).json()

    upload(api, manager, f"{HEADER}\nVAN001,61500\n")

    after = api.get(f"/vehicles/{fleet['VAN001']['id']}", headers=manager).json()
    assert after["service_baseline_odometer"] == before["service_baseline_odometer"]
    assert after["service_status"]["is_due"] is True
