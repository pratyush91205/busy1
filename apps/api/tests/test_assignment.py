"""Technician assignment and notes (spec 05, rules 12-17)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest_services import advance_to, assign, make_service, make_vehicle


# --- assignment --------------------------------------------------------------


def test_a_manager_assigns_and_unassigns(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 12."""
    assigned = api.post(
        f"/services/{service['id']}/technicians",
        json={"technician_id": people["tech"]},
        headers=manager,
    )
    assert assigned.status_code == 200
    assert [t["id"] for t in assigned.json()["technicians"]] == [people["tech"]]

    removed = api.delete(
        f"/services/{service['id']}/technicians/{people['tech']}", headers=manager
    )
    assert removed.status_code == 204

    after = api.get(f"/services/{service['id']}", headers=manager).json()
    assert after["technicians"] == []


def test_a_record_takes_several_technicians(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Many-to-many, through the join table."""
    assign(api, manager, service["id"], people["tech"])
    assign(api, manager, service["id"], people["other_tech"])

    record = api.get(f"/services/{service['id']}", headers=manager).json()

    assert {t["id"] for t in record["technicians"]} == {
        people["tech"],
        people["other_tech"],
    }


def test_a_technician_cannot_assign_anyone(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 12, including assigning themselves to a record they can see."""
    assign(api, manager, service["id"], people["tech"])

    response = api.post(
        f"/services/{service['id']}/technicians",
        json={"technician_id": people["other_tech"]},
        headers=tech,
    )

    assert response.status_code == 403


def test_a_technician_cannot_unassign_themselves(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 12: walking off a job is a manager's decision to record."""
    assign(api, manager, service["id"], people["tech"])

    response = api.delete(
        f"/services/{service['id']}/technicians/{people['tech']}", headers=tech
    )

    assert response.status_code == 403


def test_a_manager_cannot_be_assigned_to_service_work(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 13."""
    response = api.post(
        f"/services/{service['id']}/technicians",
        json={"technician_id": people["manager"]},
        headers=manager,
    )

    assert response.status_code == 409
    assert "fleet_manager" in response.json()["detail"]


def test_assigning_an_unknown_user_is_not_found(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    response = api.post(
        f"/services/{service['id']}/technicians",
        json={"technician_id": 999_999},
        headers=manager,
    )

    assert response.status_code == 404


def test_assigning_the_same_technician_twice_is_refused(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 14. The composite primary key also refuses it underneath."""
    assign(api, manager, service["id"], people["tech"])

    response = api.post(
        f"/services/{service['id']}/technicians",
        json={"technician_id": people["tech"]},
        headers=manager,
    )

    assert response.status_code == 409
    assert "already assigned" in response.json()["detail"].lower()


def test_unassigning_someone_who_is_not_assigned_is_not_found(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 14."""
    response = api.delete(
        f"/services/{service['id']}/technicians/{people['tech']}", headers=manager
    )

    assert response.status_code == 404


def test_a_completed_record_refuses_assignment_changes(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """Rule 15: who worked on it is part of its history."""
    assign(api, manager, service["id"], people["tech"])
    advance_to(api, manager, service["id"], "completed")

    added = api.post(
        f"/services/{service['id']}/technicians",
        json={"technician_id": people["other_tech"]},
        headers=manager,
    )
    removed = api.delete(
        f"/services/{service['id']}/technicians/{people['tech']}", headers=manager
    )

    assert added.status_code == 409
    assert removed.status_code == 409


def test_a_technician_keeps_assignments_across_vehicles(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """The brief's "assignments across all vehicles"."""
    second = make_vehicle(api, manager, registration_number="VAN002")
    elsewhere = make_service(api, manager, second["id"], "Tyre change")

    assign(api, manager, service["id"], people["tech"])
    assign(api, manager, elsewhere["id"], people["tech"])

    listed = api.get(
        "/services", params={"technician_id": people["tech"]}, headers=manager
    ).json()

    assert listed["total"] == 2


# --- notes -------------------------------------------------------------------


def test_a_manager_and_an_assigned_technician_may_add_notes(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    """Rule 16."""
    assign(api, manager, service["id"], people["tech"])

    by_tech = api.post(
        f"/services/{service['id']}/notes",
        json={"content": "Pads worn to 2mm"},
        headers=tech,
    )
    by_manager = api.post(
        f"/services/{service['id']}/notes",
        json={"content": "Parts ordered"},
        headers=manager,
    )

    assert by_tech.status_code == 201
    assert by_tech.json()["author"]["full_name"] == "Sam Okafor"
    assert by_manager.status_code == 201

    notes = api.get(f"/services/{service['id']}/notes", headers=manager).json()
    assert [note["content"] for note in notes] == ["Pads worn to 2mm", "Parts ordered"]


def test_an_unassigned_technician_cannot_add_a_note(
    api: TestClient, other_tech: dict[str, str], service: dict
) -> None:
    """Rule 16. 404, because they cannot see the record at all."""
    response = api.post(
        f"/services/{service['id']}/notes", json={"content": "x"}, headers=other_tech
    )

    assert response.status_code == 404


def test_a_blank_note_is_refused(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    response = api.post(
        f"/services/{service['id']}/notes", json={"content": "   "}, headers=manager
    )

    assert response.status_code == 422


def test_no_route_edits_or_deletes_a_note(api: TestClient) -> None:
    """Rule 17: notes are append-only."""
    paths = api.app.openapi()["paths"]  # type: ignore[attr-defined]
    note_paths = {
        path: methods for path, methods in paths.items() if path.endswith("/notes")
    }

    assert note_paths
    for methods in note_paths.values():
        assert set(methods) <= {"get", "post"}, methods

    # And no route addresses an individual note, which is the only way an
    # edit or delete could be added later without noticing.
    assert not any("/notes/" in path for path in paths)
