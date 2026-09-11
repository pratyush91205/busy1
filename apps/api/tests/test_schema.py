"""The database enforces the invariants it should, not just the service layer.

Each test drives raw SQL rather than the ORM: the point is that PostgreSQL
itself refuses, so a future code path that bypasses the service layer cannot
write data the rest of the system assumes is impossible.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

EXPECTED_TABLES = {
    "users",
    "vehicles",
    "service_records",
    "service_technicians",
    "service_notes",
    "audit_events",
    "overdue_alert_dismissals",
}

EXPECTED_INDEXES = {
    "ix_vehicles_is_archived",
    "ix_service_records_vehicle_id",
    "ix_service_records_status",
    "ix_service_records_scheduled_date",
    "ix_service_records_updated_at",
    "ix_service_records_due_since",
    "ix_service_technicians_technician_id",
    "ix_service_notes_service_id",
    "ix_audit_events_service_id_created_at",
}


def test_every_table_and_index_exists(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())

    assert EXPECTED_TABLES <= tables
    # The walking skeleton's table is gone, dropped by migration 0002.
    assert "deployment_check" not in tables

    indexes = {
        index["name"]
        for table in EXPECTED_TABLES
        for index in inspector.get_indexes(table)
        if index["name"]
    }
    assert EXPECTED_INDEXES <= indexes


def test_service_records_carries_due_since_and_cycle_number(
    migrated_engine: Engine,
) -> None:
    columns = {
        column["name"]: column for column in inspect(migrated_engine).get_columns("service_records")
    }

    assert "due_since" in columns, "the overdue clock must be persisted, not recomputed"
    assert "cycle_number" in columns, "the service cycle identifier must exist from the start"
    assert columns["due_since"]["type"].timezone is True


def test_duplicate_registration_number_is_rejected(clean_db: Engine) -> None:
    insert_vehicle(clean_db, "VAN001")

    with pytest.raises(IntegrityError):
        insert_vehicle(clean_db, "VAN001")


def test_negative_odometer_is_rejected(clean_db: Engine) -> None:
    with pytest.raises(IntegrityError):
        insert_vehicle(clean_db, "VAN002", odometer=-1)


def test_unknown_role_is_rejected(clean_db: Engine) -> None:
    with pytest.raises(IntegrityError):
        insert_user(clean_db, "admin@example.com", role="admin")


def test_overdue_is_not_a_storable_status(clean_db: Engine) -> None:
    """Overdue is derived. Storing it would give the system two sources of truth."""
    vehicle_id = insert_vehicle(clean_db, "VAN003")

    with pytest.raises(IntegrityError):
        insert_service(clean_db, vehicle_id, status="overdue")


def test_zero_service_interval_is_rejected(clean_db: Engine) -> None:
    """A zero interval would make a vehicle permanently due."""
    with pytest.raises(IntegrityError):
        insert_vehicle(clean_db, "VAN004", date_interval=0)


def test_blank_description_is_rejected(clean_db: Engine) -> None:
    vehicle_id = insert_vehicle(clean_db, "VAN005")

    with pytest.raises(IntegrityError):
        insert_service(clean_db, vehicle_id, description="   ")


def test_service_record_needs_a_real_vehicle(clean_db: Engine) -> None:
    with pytest.raises(IntegrityError):
        insert_service(clean_db, vehicle_id=999_999)


def test_technician_cannot_be_assigned_twice(clean_db: Engine) -> None:
    vehicle_id = insert_vehicle(clean_db, "VAN006")
    service_id = insert_service(clean_db, vehicle_id)
    technician_id = insert_user(clean_db, "tech@example.com")

    assign(clean_db, service_id, technician_id)

    with pytest.raises(IntegrityError):
        assign(clean_db, service_id, technician_id)


def test_one_cycle_number_per_vehicle(clean_db: Engine) -> None:
    vehicle_id = insert_vehicle(clean_db, "VAN007")
    insert_service(clean_db, vehicle_id, cycle_number=1)

    with pytest.raises(IntegrityError):
        insert_service(clean_db, vehicle_id, cycle_number=1)


def test_audit_events_cannot_be_updated_or_deleted(clean_db: Engine) -> None:
    """Append-only, enforced by the database - this is not an ORM convention."""
    vehicle_id = insert_vehicle(clean_db, "VAN008")
    service_id = insert_service(clean_db, vehicle_id)
    actor_id = insert_user(clean_db, "manager@example.com", role="fleet_manager")

    with clean_db.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events (service_id, actor_id, event_type, new_value) "
                "VALUES (:service_id, :actor_id, 'service_created', 'due')"
            ),
            {"service_id": service_id, "actor_id": actor_id},
        )

    with pytest.raises(DBAPIError, match="append-only"):
        with clean_db.begin() as connection:
            connection.execute(text("UPDATE audit_events SET new_value = 'tampered'"))

    with pytest.raises(DBAPIError, match="append-only"):
        with clean_db.begin() as connection:
            connection.execute(text("DELETE FROM audit_events"))

    with clean_db.connect() as connection:
        remaining = connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one()
    assert remaining == 1


def test_a_vehicle_with_history_cannot_be_deleted(clean_db: Engine) -> None:
    """Vehicles are archived, never destroyed; the FK makes that non-optional."""
    vehicle_id = insert_vehicle(clean_db, "VAN009")
    insert_service(clean_db, vehicle_id)

    with pytest.raises(IntegrityError):
        with clean_db.begin() as connection:
            connection.execute(
                text("DELETE FROM vehicles WHERE id = :id"), {"id": vehicle_id}
            )


# --- helpers -----------------------------------------------------------------


def insert_user(
    engine: Engine, email: str, *, role: str = "technician", name: str = "Test User"
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            text(
                "INSERT INTO users (email, full_name, password_hash, role) "
                "VALUES (:email, :name, 'not-a-real-hash', :role) RETURNING id"
            ),
            {"email": email, "name": name, "role": role},
        ).scalar_one()


def insert_vehicle(
    engine: Engine,
    registration: str,
    *,
    odometer: int = 50_000,
    date_interval: int = 180,
    mileage_interval: int = 10_000,
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            text(
                "INSERT INTO vehicles (registration_number, make, model, current_odometer, "
                "service_date_interval, service_mileage_interval) "
                "VALUES (:registration, 'Ford', 'Transit', :odometer, :date_interval, "
                ":mileage_interval) RETURNING id"
            ),
            {
                "registration": registration,
                "odometer": odometer,
                "date_interval": date_interval,
                "mileage_interval": mileage_interval,
            },
        ).scalar_one()


def insert_service(
    engine: Engine,
    vehicle_id: int,
    *,
    status: str = "due",
    description: str = "Brake inspection",
    cycle_number: int = 1,
) -> int:
    with engine.begin() as connection:
        return connection.execute(
            text(
                "INSERT INTO service_records (vehicle_id, cycle_number, description, status) "
                "VALUES (:vehicle_id, :cycle_number, :description, :status) RETURNING id"
            ),
            {
                "vehicle_id": vehicle_id,
                "cycle_number": cycle_number,
                "description": description,
                "status": status,
            },
        ).scalar_one()


def assign(engine: Engine, service_id: int, technician_id: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO service_technicians (service_id, technician_id) "
                "VALUES (:service_id, :technician_id)"
            ),
            {"service_id": service_id, "technician_id": technician_id},
        )
