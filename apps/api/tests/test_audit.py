"""The immutable service timeline (spec 05, audit events).

The timeline is read through the API here. That the table itself refuses UPDATE
and DELETE is proved against raw SQL in test_schema.py - a trigger, not an
absent endpoint - so these tests cover what the application writes and what it
exposes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest_services import assign, move


def timeline(api: TestClient, headers: dict[str, str], service_id: int) -> list[dict]:
    response = api.get(f"/services/{service_id}/timeline", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_creating_a_record_writes_the_first_event(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    events = timeline(api, manager, service["id"])

    assert len(events) == 1
    created = events[0]
    assert created["event_type"] == "service_created"
    assert created["new_value"] == "due"
    assert created["actor"]["id"] == people["manager"]
    assert created["event_metadata"]["cycle_number"] == 1


def test_a_status_change_records_both_states_and_the_actor(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    assign(api, manager, service["id"], people["tech"])
    move(api, manager, service["id"], "booked", scheduled_date="2026-10-01")
    move(api, tech, service["id"], "in_service")

    changes = [
        event
        for event in timeline(api, manager, service["id"])
        if event["event_type"] == "status_changed"
    ]

    assert [(c["old_value"], c["new_value"]) for c in changes] == [
        ("due", "booked"),
        ("booked", "in_service"),
    ]
    # The actor is whoever made that particular change, not whoever owns the
    # record - which is the entire point of recording it.
    assert changes[0]["actor"]["id"] == people["manager"]
    assert changes[1]["actor"]["id"] == people["tech"]
    assert changes[0]["event_metadata"]["scheduled_date"] == "2026-10-01"


def test_assignment_and_unassignment_are_both_recorded(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    assign(api, manager, service["id"], people["tech"])
    api.delete(
        f"/services/{service['id']}/technicians/{people['tech']}", headers=manager
    )

    events = timeline(api, manager, service["id"])
    assigned = next(e for e in events if e["event_type"] == "technician_assigned")
    unassigned = next(e for e in events if e["event_type"] == "technician_unassigned")

    assert assigned["new_value"] == str(people["tech"])
    assert assigned["event_metadata"]["technician_name"] == "Sam Okafor"
    # The name is kept on the event so the timeline still reads correctly after
    # the assignment row is gone.
    assert unassigned["old_value"] == str(people["tech"])
    assert unassigned["event_metadata"]["technician_name"] == "Sam Okafor"


def test_adding_a_note_is_recorded(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    note = api.post(
        f"/services/{service['id']}/notes",
        json={"content": "Parts ordered"},
        headers=manager,
    ).json()

    events = timeline(api, manager, service["id"])
    added = next(e for e in events if e["event_type"] == "note_added")

    assert added["new_value"] == str(note["id"])


def test_completion_records_the_odometer(
    api: TestClient, manager: dict[str, str], service: dict
) -> None:
    move(api, manager, service["id"], "booked", scheduled_date="2026-10-01")
    move(api, manager, service["id"], "in_service")
    move(api, manager, service["id"], "completed", completion_odometer=61_500)

    completed = [
        e
        for e in timeline(api, manager, service["id"])
        if e["new_value"] == "completed"
    ][0]

    assert completed["event_metadata"]["completion_odometer"] == 61_500


def test_the_timeline_is_oldest_first_and_complete(
    api: TestClient, manager: dict[str, str], people: dict[str, int], service: dict
) -> None:
    """One full cycle, and every step accounted for in the order it happened."""
    assign(api, manager, service["id"], people["tech"])
    api.post(
        f"/services/{service['id']}/notes",
        json={"content": "Parts ordered"},
        headers=manager,
    )
    move(api, manager, service["id"], "booked", scheduled_date="2026-10-01")
    move(api, manager, service["id"], "in_service")
    move(api, manager, service["id"], "completed", completion_odometer=61_500)

    events = timeline(api, manager, service["id"])

    assert [event["event_type"] for event in events] == [
        "service_created",
        "technician_assigned",
        "note_added",
        "status_changed",
        "status_changed",
        "status_changed",
    ]
    timestamps = [event["created_at"] for event in events]
    assert timestamps == sorted(timestamps)


def test_a_technician_reads_the_timeline_of_their_own_record_only(
    api: TestClient,
    manager: dict[str, str],
    tech: dict[str, str],
    other_tech: dict[str, str],
    people: dict[str, int],
    service: dict,
) -> None:
    assign(api, manager, service["id"], people["tech"])

    assert api.get(f"/services/{service['id']}/timeline", headers=tech).status_code == 200
    assert (
        api.get(f"/services/{service['id']}/timeline", headers=other_tech).status_code
        == 404
    )


def test_no_route_edits_or_deletes_an_audit_event(api: TestClient) -> None:
    """Append-only at the API surface as well as in the database.

    The triggers in migration 0002 are the real guarantee; this asserts the
    application never offers the door in the first place.
    """
    paths = api.app.openapi()["paths"]  # type: ignore[attr-defined]

    timeline_paths = {
        path: methods for path, methods in paths.items() if "timeline" in path
    }
    assert timeline_paths
    for methods in timeline_paths.values():
        assert set(methods) == {"get"}, methods

    assert not any("audit" in path for path in paths)
