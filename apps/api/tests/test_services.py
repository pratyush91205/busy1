"""Service record creation, editing and visibility (spec 05, rules 1-6, 18-19)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from .conftest_services import (
    advance_to,
    assign,
    make_service,
    make_vehicle,
    move,
)


# --- creation ----------------------------------------------------------------


def test_a_manager_opens_a_service_record(
    api: TestClient, manager: dict[str, str], vehicle: dict
) -> None:
    """Rules 1 and 4."""
    service = make_service(api, manager, vehicle["id"])

    assert service["status"] == "due"
    assert service["cycle_number"] == 1
    assert service["due_since"] is not None, "the overdue clock has to start somewhere"
    assert service["vehicle"]["registration_number"] == "VAN001"
    assert service["technicians"] == []


def test_a_technician_cannot_open_one(
    api: TestClient, tech: dict[str, str], vehicle: dict
) -> None:
    """Rule 1."""
    response = api.post(
        "/services",
        json={"vehicle_id": vehicle["id"], "description": "Brake inspection"},
        headers=tech,
    )

    assert response.status_code == 403


def test_a_client_supplied_status_is_refused(
    api: TestClient, manager: dict[str, str], vehicle: dict
) -> None:
    """Rule 4: the client does not choose where a record starts."""
    response = api.post(
        "/services",
        json={
            "vehicle_id": vehicle["id"],
            "description": "Brake inspection",
            "status": "completed",
        },
        headers=manager,
    )

    # The create schema has no status field at all, so this is not a value the
    # server has to remember to ignore.
    assert response.status_code in {201, 422}
    if response.status_code == 201:
        assert response.json()["status"] == "due"


def test_an_archived_vehicle_takes_no_new_records(
    api: TestClient, manager: dict[str, str], vehicle: dict
) -> None:
    """Rule 2."""
    api.post(f"/vehicles/{vehicle['id']}/archive", headers=manager)

    response = api.post(
        "/services",
        json={"vehicle_id": vehicle["id"], "description": "Brake inspection"},
        headers=manager,
    )

    assert response.status_code == 409
    assert "archived" in response.json()["detail"].lower()


def test_a_vehicle_may_have_only_one_open_record(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    """Rule 3: without this, "the current cycle" has no meaning."""
    response = api.post(
        "/services",
        json={"vehicle_id": vehicle["id"], "description": "Oil change"},
        headers=manager,
    )

    assert response.status_code == 409
    assert "open service record" in response.json()["detail"].lower()


def test_completing_a_record_frees_the_vehicle_for_the_next_cycle(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    """Rule 3, the other half: cycles follow one another."""
    advance_to(api, manager, service["id"], "completed")

    second = make_service(api, manager, vehicle["id"], "Oil change")

    assert second["cycle_number"] == 2
    assert second["status"] == "due"


def test_a_record_needs_a_real_vehicle(
    api: TestClient, manager: dict[str, str]
) -> None:
    response = api.post(
        "/services", json={"vehicle_id": 999_999, "description": "x"}, headers=manager
    )

    assert response.status_code == 404


@pytest.mark.parametrize("description", ["", "   "])
def test_a_blank_description_is_refused(
    api: TestClient, manager: dict[str, str], vehicle: dict, description: str
) -> None:
    response = api.post(
        "/services",
        json={"vehicle_id": vehicle["id"], "description": description},
        headers=manager,
    )

    assert response.status_code in {409, 422}


# --- editing the description -------------------------------------------------


def test_a_manager_edits_the_description(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    """Rule 5."""
    response = api.patch(
        f"/services/{service['id']}",
        json={"description": "Brake pads and discs"},
        headers=manager,
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Brake pads and discs"


def test_an_assigned_technician_edits_the_description(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 5."""
    assign(api, manager, service["id"], people["tech"])

    response = api.patch(
        f"/services/{service['id']}",
        json={"description": "Pads worn to 2mm"},
        headers=tech,
    )

    assert response.status_code == 200


def test_an_unassigned_technician_cannot_edit(
    api: TestClient, other_tech: dict[str, str], service: dict
) -> None:
    """Rule 5. 404 rather than 403 - see rule 18."""
    response = api.patch(
        f"/services/{service['id']}", json={"description": "nope"}, headers=other_tech
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "smuggled",
    [
        {"description": "ok", "status": "completed"},
        {"description": "ok", "vehicle_id": 2},
        {"description": "ok", "technician_ids": [1, 2]},
        {"description": "ok", "technicians": [1]},
    ],
)
def test_the_description_endpoint_accepts_nothing_but_a_description(
    api: TestClient, manager: dict[str, str], service: dict, smuggled: dict
) -> None:
    """Rule 6, the reason this endpoint is separate from assignment.

    An assigned technician may edit a description. If this schema also took a
    status or a technician list, that permission would silently become the
    permission to reassign the record or skip the lifecycle.
    """
    response = api.patch(f"/services/{service['id']}", json=smuggled, headers=manager)

    assert response.status_code == 422, response.text


# --- visibility --------------------------------------------------------------


def test_a_technician_sees_only_their_own_records_across_vehicles(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    vehicle: dict,
    service: dict,
) -> None:
    """Rule 18, and the brief's "assignments across all vehicles"."""
    second_vehicle = make_vehicle(api, manager, registration_number="VAN002")
    mine_elsewhere = make_service(api, manager, second_vehicle["id"], "Tyre change")
    third_vehicle = make_vehicle(api, manager, registration_number="VAN003")
    not_mine = make_service(api, manager, third_vehicle["id"], "Not mine")

    assign(api, manager, service["id"], people["tech"])
    assign(api, manager, mine_elsewhere["id"], people["tech"])
    assign(api, manager, not_mine["id"], people["other_tech"])

    listed = api.get("/services", headers=tech).json()

    assert listed["total"] == 2, "the count must describe what they can see"
    assert {item["id"] for item in listed["items"]} == {
        service["id"],
        mine_elsewhere["id"],
    }
    assert {item["vehicle"]["registration_number"] for item in listed["items"]} == {
        "VAN001",
        "VAN002",
    }


def test_a_technician_reading_someone_elses_record_gets_not_found(
    api: TestClient,
    manager: dict[str, str],
    other_tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 18: 403 would confirm the id exists."""
    assign(api, manager, service["id"], people["tech"])

    response = api.get(f"/services/{service['id']}", headers=other_tech)

    assert response.status_code == 404


def test_a_manager_sees_everything(
    api: TestClient,
    manager: dict[str, str],
    people: dict[str, int],
    vehicle: dict,
    service: dict,
) -> None:
    """Rule 19."""
    second = make_vehicle(api, manager, registration_number="VAN002")
    make_service(api, manager, second["id"], "Tyre change")

    listed = api.get("/services", headers=manager).json()

    assert listed["total"] == 2


def test_a_technician_cannot_widen_their_scope_with_a_filter(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """The technician_id filter is overridden by the server, not trusted."""
    assign(api, manager, service["id"], people["other_tech"])

    listed = api.get(
        "/services", params={"technician_id": people["other_tech"]}, headers=tech
    ).json()

    assert listed["total"] == 0


# --- filtering ---------------------------------------------------------------


def test_filtering_by_vehicle_status_and_search(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    second = make_vehicle(api, manager, registration_number="VAN002")
    other = make_service(api, manager, second["id"], "Tyre change")
    advance_to(api, manager, other["id"], "booked")

    by_vehicle = api.get(
        "/services", params={"vehicle_id": vehicle["id"]}, headers=manager
    ).json()
    assert [item["id"] for item in by_vehicle["items"]] == [service["id"]]

    by_status = api.get("/services", params={"status": "booked"}, headers=manager).json()
    assert [item["id"] for item in by_status["items"]] == [other["id"]]

    by_search = api.get("/services", params={"search": "tyre"}, headers=manager).json()
    assert [item["id"] for item in by_search["items"]] == [other["id"]]


def test_filtering_by_technician_does_not_duplicate_multi_technician_records(
    api: TestClient,
    manager: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """A join to the assignment table would return this record twice."""
    assign(api, manager, service["id"], people["tech"])
    assign(api, manager, service["id"], people["other_tech"])

    listed = api.get("/services", headers=manager).json()

    assert listed["total"] == 1
    assert len(listed["items"]) == 1
    assert len(listed["items"][0]["technicians"]) == 2


def test_sorting_by_status_follows_the_lifecycle_not_the_alphabet(
    api: TestClient, manager: dict[str, str], vehicle: dict, service: dict
) -> None:
    """Alphabetically booked < completed < due < in_service - sorted, and useless."""
    for registration, target in [
        ("VAN002", "booked"),
        ("VAN003", "in_service"),
        ("VAN004", "completed"),
    ]:
        other = make_vehicle(api, manager, registration_number=registration)
        record = make_service(api, manager, other["id"], f"{target} work")
        advance_to(api, manager, record["id"], target)

    ascending = api.get(
        "/services", params={"sort": "status", "order": "asc"}, headers=manager
    ).json()
    descending = api.get(
        "/services", params={"sort": "status", "order": "desc"}, headers=manager
    ).json()

    lifecycle = ["due", "booked", "in_service", "completed"]
    assert [item["status"] for item in ascending["items"]] == lifecycle
    assert [item["status"] for item in descending["items"]] == lifecycle[::-1]
