"""Vehicle rules (spec 04).

Every request goes through the real routes with a real token, so each test
exercises authorization and the rule together - which is the pair that matters.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.main import create_app

from .conftest import build_test_settings, client_for
from .helpers import auth_header, create_user

VEHICLE = {
    "registration_number": "VAN001",
    "make": "Ford",
    "model": "Transit",
    "current_odometer": 50_000,
    "service_date_interval": 180,
    "service_mileage_interval": 10_000,
}


@pytest.fixture
def api(clean_db: Engine) -> Iterator[TestClient]:
    with client_for(create_app(build_test_settings()), clean_db) as test_client:
        yield test_client


@pytest.fixture
def manager(api: TestClient, clean_db: Engine) -> dict[str, str]:
    create_user(clean_db, "manager@fleet.example", "Morgan Reed", "fleet_manager")
    return auth_header(api, "manager@fleet.example")


@pytest.fixture
def technician(api: TestClient, clean_db: Engine) -> dict[str, str]:
    create_user(clean_db, "tech@fleet.example", "Sam Okafor", "technician")
    return auth_header(api, "tech@fleet.example")


def create(api: TestClient, manager: dict[str, str], **overrides: object) -> dict:
    response = api.post("/vehicles", json=VEHICLE | overrides, headers=manager)
    assert response.status_code == 201, response.text
    return response.json()


# --- authorization -----------------------------------------------------------


def test_a_manager_creates_a_vehicle(api: TestClient, manager: dict[str, str]) -> None:
    """Rule 1."""
    vehicle = create(api, manager)

    assert vehicle["registration_number"] == "VAN001"
    assert vehicle["is_archived"] is False


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/vehicles", VEHICLE),
        ("patch", "/vehicles/{id}", {"make": "Vauxhall"}),
        ("post", "/vehicles/{id}/archive", None),
        ("post", "/vehicles/{id}/restore", None),
    ],
)
def test_a_technician_is_refused_every_mutation(
    api: TestClient,
    manager: dict[str, str],
    technician: dict[str, str],
    method: str,
    path: str,
    body: dict | None,
) -> None:
    """Rule 1. Hiding the button is not the mechanism; this is."""
    vehicle = create(api, manager)

    response = api.request(
        method.upper(),
        path.format(id=vehicle["id"]),
        json=body,
        headers=technician,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This action requires the fleet_manager role"


def test_a_technician_can_read_the_fleet(
    api: TestClient, manager: dict[str, str], technician: dict[str, str]
) -> None:
    """Rule 1: they need to know which vehicle a job is on."""
    vehicle = create(api, manager)

    assert api.get("/vehicles", headers=technician).status_code == 200
    assert api.get(f"/vehicles/{vehicle['id']}", headers=technician).status_code == 200


def test_listing_without_a_token_is_unauthorized(api: TestClient) -> None:
    assert api.get("/vehicles").status_code == 401


# --- registration ------------------------------------------------------------


@pytest.mark.parametrize("duplicate", ["VAN001", "van001", "  van001  "])
def test_a_duplicate_registration_is_refused(
    api: TestClient, manager: dict[str, str], duplicate: str
) -> None:
    """Rule 2. Case and whitespace do not make it a different vehicle."""
    create(api, manager)

    response = api.post(
        "/vehicles", json=VEHICLE | {"registration_number": duplicate}, headers=manager
    )

    assert response.status_code == 409
    assert "VAN001" in response.json()["detail"]


def test_registration_is_stored_normalised(
    api: TestClient, manager: dict[str, str]
) -> None:
    vehicle = create(api, manager, registration_number="  van 001 ")

    assert vehicle["registration_number"] == "VAN 001"


def test_renaming_onto_another_vehicles_registration_is_refused(
    api: TestClient, manager: dict[str, str]
) -> None:
    create(api, manager)
    other = create(api, manager, registration_number="VAN002")

    response = api.patch(
        f"/vehicles/{other['id']}",
        json={"registration_number": "VAN001"},
        headers=manager,
    )

    assert response.status_code == 409


def test_renaming_a_vehicle_to_its_own_registration_is_allowed(
    api: TestClient, manager: dict[str, str]
) -> None:
    """It collides with itself, which is not a conflict."""
    vehicle = create(api, manager)

    response = api.patch(
        f"/vehicles/{vehicle['id']}",
        json={"registration_number": "VAN001"},
        headers=manager,
    )

    assert response.status_code == 200


# --- odometer ----------------------------------------------------------------


def test_raising_the_odometer_succeeds(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 3."""
    vehicle = create(api, manager)

    response = api.patch(
        f"/vehicles/{vehicle['id']}", json={"current_odometer": 51_000}, headers=manager
    )

    assert response.status_code == 200
    assert response.json()["current_odometer"] == 51_000


def test_lowering_the_odometer_is_refused_and_changes_nothing(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 3. The rejection must not be a partial write."""
    vehicle = create(api, manager)

    response = api.patch(
        f"/vehicles/{vehicle['id']}",
        json={"current_odometer": 49_000, "make": "Vauxhall"},
        headers=manager,
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "49000" in detail and "50000" in detail

    unchanged = api.get(f"/vehicles/{vehicle['id']}", headers=manager).json()
    assert unchanged["current_odometer"] == 50_000
    assert unchanged["make"] == "Ford", "the rejected request wrote part of itself"


def test_an_equal_odometer_reading_is_accepted(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 3: re-sending today's reading is a no-op, not an error."""
    vehicle = create(api, manager)

    response = api.patch(
        f"/vehicles/{vehicle['id']}", json={"current_odometer": 50_000}, headers=manager
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "invalid",
    [
        {"current_odometer": -1},
        {"service_date_interval": 0},
        {"service_mileage_interval": 0},
        {"service_date_interval": -30},
    ],
)
def test_out_of_range_values_are_unprocessable_not_a_server_error(
    api: TestClient, manager: dict[str, str], invalid: dict
) -> None:
    """Rule 4: a readable 422 rather than an IntegrityError surfacing as 500."""
    response = api.post("/vehicles", json=VEHICLE | invalid, headers=manager)

    assert response.status_code == 422


# --- archive and restore -----------------------------------------------------


def test_archiving_keeps_the_row_and_the_vehicle_readable(
    api: TestClient, manager: dict[str, str], clean_db: Engine
) -> None:
    """Rule 5: a soft delete, so history survives."""
    vehicle = create(api, manager)

    assert api.post(f"/vehicles/{vehicle['id']}/archive", headers=manager).status_code == 200

    with clean_db.connect() as connection:
        rows = connection.execute(text("SELECT count(*) FROM vehicles")).scalar_one()
    assert rows == 1

    read = api.get(f"/vehicles/{vehicle['id']}", headers=manager)
    assert read.status_code == 200
    assert read.json()["is_archived"] is True


def test_an_archived_vehicle_refuses_edits_until_restored(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 6."""
    vehicle = create(api, manager)
    api.post(f"/vehicles/{vehicle['id']}/archive", headers=manager)

    refused = api.patch(
        f"/vehicles/{vehicle['id']}", json={"make": "Vauxhall"}, headers=manager
    )
    assert refused.status_code == 409
    assert "archived" in refused.json()["detail"].lower()

    assert api.post(f"/vehicles/{vehicle['id']}/restore", headers=manager).status_code == 200
    assert (
        api.patch(
            f"/vehicles/{vehicle['id']}", json={"make": "Vauxhall"}, headers=manager
        ).status_code
        == 200
    )


def test_archiving_twice_is_refused(api: TestClient, manager: dict[str, str]) -> None:
    """Rule 7: a no-op reporting success hides a mistake."""
    vehicle = create(api, manager)
    api.post(f"/vehicles/{vehicle['id']}/archive", headers=manager)

    assert api.post(f"/vehicles/{vehicle['id']}/archive", headers=manager).status_code == 409


def test_restoring_a_live_vehicle_is_refused(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 7."""
    vehicle = create(api, manager)

    assert api.post(f"/vehicles/{vehicle['id']}/restore", headers=manager).status_code == 409


def test_an_unknown_vehicle_is_not_found(
    api: TestClient, manager: dict[str, str]
) -> None:
    assert api.get("/vehicles/999999", headers=manager).status_code == 404
    assert api.post("/vehicles/999999/archive", headers=manager).status_code == 404


# --- listing -----------------------------------------------------------------


def test_the_default_list_excludes_archived_vehicles(
    api: TestClient, manager: dict[str, str]
) -> None:
    """Rule 8."""
    live = create(api, manager)
    archived = create(api, manager, registration_number="VAN002")
    api.post(f"/vehicles/{archived['id']}/archive", headers=manager)

    default = api.get("/vehicles", headers=manager).json()
    assert [v["id"] for v in default["items"]] == [live["id"]]
    assert default["total"] == 1

    including = api.get(
        "/vehicles", params={"include_archived": True}, headers=manager
    ).json()
    assert including["total"] == 2


@pytest.mark.parametrize("term", ["van00", "ford", "TRANSIT", "Tran"])
def test_search_matches_registration_make_and_model_case_insensitively(
    api: TestClient, manager: dict[str, str], term: str
) -> None:
    create(api, manager)
    create(api, manager, registration_number="TRK009", make="Volvo", model="FH16")

    found = api.get("/vehicles", params={"search": term}, headers=manager).json()

    assert [v["registration_number"] for v in found["items"]] == ["VAN001"]


def test_a_search_of_only_wildcards_matches_nothing(
    api: TestClient, manager: dict[str, str]
) -> None:
    """The LIKE wildcards are escaped, so "%" is a literal, not "everything"."""
    create(api, manager)

    found = api.get("/vehicles", params={"search": "%"}, headers=manager).json()

    assert found["total"] == 0


def test_sorting_by_odometer_runs_both_ways(
    api: TestClient, manager: dict[str, str]
) -> None:
    create(api, manager, registration_number="VAN001", current_odometer=10_000)
    create(api, manager, registration_number="VAN002", current_odometer=30_000)
    create(api, manager, registration_number="VAN003", current_odometer=20_000)

    ascending = api.get(
        "/vehicles", params={"sort": "current_odometer", "order": "asc"}, headers=manager
    ).json()
    descending = api.get(
        "/vehicles",
        params={"sort": "current_odometer", "order": "desc"},
        headers=manager,
    ).json()

    assert [v["current_odometer"] for v in ascending["items"]] == [10_000, 20_000, 30_000]
    assert [v["current_odometer"] for v in descending["items"]] == [30_000, 20_000, 10_000]


def test_an_unknown_sort_field_is_rejected(
    api: TestClient, manager: dict[str, str]
) -> None:
    """The sort column is an enum, not an interpolated string."""
    response = api.get("/vehicles", params={"sort": "password_hash"}, headers=manager)

    assert response.status_code == 422


def test_pagination_returns_a_slice_and_honest_totals(
    api: TestClient, manager: dict[str, str]
) -> None:
    for index in range(5):
        create(api, manager, registration_number=f"VAN00{index}")

    page_two = api.get(
        "/vehicles", params={"page": 2, "limit": 2}, headers=manager
    ).json()

    assert [v["registration_number"] for v in page_two["items"]] == ["VAN002", "VAN003"]
    assert page_two["total"] == 5
    assert page_two["total_pages"] == 3
    assert page_two["page"] == 2


def test_a_page_past_the_end_is_empty_not_an_error(
    api: TestClient, manager: dict[str, str]
) -> None:
    create(api, manager)

    response = api.get("/vehicles", params={"page": 99}, headers=manager)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_the_page_size_is_capped(api: TestClient, manager: dict[str, str]) -> None:
    """An unbounded limit turns a list endpoint into a full-table export."""
    assert api.get("/vehicles", params={"limit": 1000}, headers=manager).status_code == 422


# --- surface -----------------------------------------------------------------


def test_no_route_deletes_a_vehicle(api: TestClient) -> None:
    """Rule 9. Archive is the only removal."""
    paths = api.app.openapi()["paths"]  # type: ignore[attr-defined]

    assert not any("delete" in methods for methods in paths.values())
