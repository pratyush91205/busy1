"""Fixtures shared by the service-record test modules.

Imported as a plugin from conftest so all four service test files get the same
world: one manager, two technicians, one vehicle, and helpers that drive the
real API rather than writing rows behind it.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.main import create_app

from .conftest import build_test_settings, client_for
from .helpers import auth_header, create_user

MANAGER_EMAIL = "manager@fleet.example"
TECH_EMAIL = "tech@fleet.example"
OTHER_TECH_EMAIL = "other@fleet.example"

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
def people(api: TestClient, clean_db: Engine) -> dict[str, int]:
    """Everyone the service tests need, created before any token is issued."""
    return {
        "manager": create_user(clean_db, MANAGER_EMAIL, "Morgan Reed", "fleet_manager"),
        "tech": create_user(clean_db, TECH_EMAIL, "Sam Okafor", "technician"),
        "other_tech": create_user(
            clean_db, OTHER_TECH_EMAIL, "Alex Bell", "technician"
        ),
    }


@pytest.fixture
def manager(api: TestClient, people: dict[str, int]) -> dict[str, str]:
    return auth_header(api, MANAGER_EMAIL)


@pytest.fixture
def tech(api: TestClient, people: dict[str, int]) -> dict[str, str]:
    return auth_header(api, TECH_EMAIL)


@pytest.fixture
def other_tech(api: TestClient, people: dict[str, int]) -> dict[str, str]:
    return auth_header(api, OTHER_TECH_EMAIL)


@pytest.fixture
def vehicle(api: TestClient, manager: dict[str, str]) -> dict:
    return make_vehicle(api, manager)


@pytest.fixture
def service(api: TestClient, manager: dict[str, str], vehicle: dict) -> dict:
    return make_service(api, manager, vehicle["id"])


def make_vehicle(api: TestClient, manager: dict[str, str], **overrides) -> dict:
    response = api.post("/vehicles", json=VEHICLE | overrides, headers=manager)
    assert response.status_code == 201, response.text
    return response.json()


def make_service(
    api: TestClient,
    manager: dict[str, str],
    vehicle_id: int,
    description: str = "Brake inspection",
) -> dict:
    response = api.post(
        "/services",
        json={"vehicle_id": vehicle_id, "description": description},
        headers=manager,
    )
    assert response.status_code == 201, response.text
    return response.json()


def assign(
    api: TestClient, manager: dict[str, str], service_id: int, technician_id: int
) -> None:
    response = api.post(
        f"/services/{service_id}/technicians",
        json={"technician_id": technician_id},
        headers=manager,
    )
    assert response.status_code == 200, response.text


def move(
    api: TestClient,
    headers: dict[str, str],
    service_id: int,
    status: str,
    **extra,
):
    return api.post(
        f"/services/{service_id}/transition",
        json={"status": status, **extra},
        headers=headers,
    )


def advance_to(
    api: TestClient, manager: dict[str, str], service_id: int, target: str
) -> None:
    """Walk a record forward through the legal path to ``target``."""
    steps = [
        ("booked", {"scheduled_date": "2026-10-01"}),
        ("in_service", {}),
        ("completed", {"completion_odometer": 60_000}),
    ]
    for status, extra in steps:
        response = move(api, manager, service_id, status, **extra)
        assert response.status_code == 200, response.text
        if status == target:
            return
    raise AssertionError(f"{target} is not on the lifecycle path")
