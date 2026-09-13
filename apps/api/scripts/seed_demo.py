"""Seed a demo fleet.

Drives the **service layer**, not raw SQL. Seeding through ``create_vehicle``,
``create_service``, ``assign_technician`` and ``transition`` means the demo data
obeys every rule the application does, and cycle numbers, service baselines and
audit events come out right without being reproduced by hand. It also means
that if a rule is broken, seeding fails loudly rather than producing data the
UI cannot explain.

The one exception is backdating. Completions are always "now" as far as the
rules are concerned - the rules are about the present - so the script rewrites
those timestamps directly afterwards. That is the only place demo data is
written by hand, and it is marked where it happens.

    python scripts/seed_demo.py --reset

Refuses to run against a database that already has vehicles unless --reset is
given, so it cannot quietly double the fleet.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth.passwords import hash_password  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models import ServiceStatus, User, Vehicle  # noqa: E402
from app.schemas.service import TransitionRequest  # noqa: E402
from app.schemas.vehicle import VehicleCreate  # noqa: E402
from app.services import service_service, vehicle_service  # noqa: E402

PASSWORD = "demo1234"

MANAGERS = [
    ("manager@fleet.example", "Morgan Reed"),
    ("dana@fleet.example", "Dana Whitfield"),
]

TECHNICIANS = [
    ("tech@fleet.example", "Sam Okafor"),
    ("alex@fleet.example", "Alex Bell"),
    ("priya@fleet.example", "Priya Nair"),
    ("tom@fleet.example", "Tom Vasquez"),
]

# registration, make, model, odometer, date interval, mileage interval
FLEET = [
    ("VAN001", "Ford", "Transit", 52_300, 180, 10_000),
    ("VAN002", "Ford", "Transit", 76_500, 180, 10_000),
    ("VAN003", "Vauxhall", "Vivaro", 45_000, 180, 10_000),
    ("VAN004", "Vauxhall", "Vivaro", 18_400, 120, 8_000),
    ("VAN005", "Mercedes", "Sprinter", 91_200, 180, 12_000),
    ("VAN006", "Mercedes", "Sprinter", 33_750, 180, 12_000),
    ("TRK010", "Volvo", "FH16", 210_400, 90, 25_000),
    ("TRK011", "Volvo", "FH16", 154_900, 90, 25_000),
    ("TRK012", "Scania", "R450", 98_600, 90, 25_000),
    ("CAR020", "Toyota", "Corolla", 27_300, 365, 15_000),
    ("CAR021", "Toyota", "Corolla", 12_100, 365, 15_000),
    ("VAN099", "Ford", "Transit", 188_000, 180, 10_000),  # archived below
]


def main() -> int:
    args = parse_args()
    engine = get_engine()

    with Session(engine) as db:
        if db.scalar(select(func.count(Vehicle.id))):
            if not args.reset:
                print(
                    "This database already has vehicles. Re-run with --reset to "
                    "wipe and reseed.",
                    file=sys.stderr,
                )
                return 1
            wipe(db)

        managers, technicians = seed_users(db)
        seed_fleet(db, managers[0], technicians)

    print("\nDemo data seeded. Sign in with:")
    print(f"  Fleet Manager   {MANAGERS[0][0]}   {PASSWORD}")
    print(f"  Technician      {TECHNICIANS[0][0]}   {PASSWORD}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a demo fleet.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing domain data first.",
    )
    return parser.parse_args()


def wipe(db: Session) -> None:
    """TRUNCATE rather than DELETE: audit_events has a trigger refusing DELETE."""
    db.execute(
        text(
            "TRUNCATE audit_events, service_notes, service_technicians, "
            "overdue_alert_dismissals, service_records, vehicles, users "
            "RESTART IDENTITY CASCADE"
        )
    )
    db.commit()
    print("Existing data removed.")


def seed_users(db: Session) -> tuple[list[User], list[User]]:
    password_hash = hash_password(PASSWORD)

    def make(email: str, name: str, role: str) -> User:
        user = User(
            email=email, full_name=name, password_hash=password_hash, role=role
        )
        db.add(user)
        return user

    managers = [make(email, name, "fleet_manager") for email, name in MANAGERS]
    technicians = [make(email, name, "technician") for email, name in TECHNICIANS]
    db.commit()

    print(f"Seeded {len(managers)} managers and {len(technicians)} technicians.")
    return managers, technicians


def seed_fleet(db: Session, manager: User, technicians: list[User]) -> None:
    vehicles = [
        vehicle_service.create_vehicle(
            db,
            VehicleCreate(
                registration_number=registration,
                make=make,
                model=model,
                current_odometer=odometer,
                service_date_interval=date_interval,
                service_mileage_interval=mileage_interval,
            ),
            manager,
        )
        for registration, make, model, odometer, date_interval, mileage_interval in FLEET
    ]
    print(f"Seeded {len(vehicles)} vehicles.")

    # A history of completed cycles, spread over the last eight weeks so the
    # dashboard chart has shape rather than one tall bar.
    history = [(0, 1), (1, 5), (2, 12), (3, 19), (4, 33), (5, 40), (6, 54)]
    for index, (vehicle_index, days_ago) in enumerate(history):
        complete_cycle(
            db,
            vehicles[vehicle_index],
            manager,
            technicians[index % len(technicians)],
            days_ago,
        )

    # Live work, one per vehicle, covering every lifecycle state.
    in_progress(db, vehicles[2], manager, technicians[0], ServiceStatus.IN_SERVICE)
    in_progress(db, vehicles[3], manager, technicians[1], ServiceStatus.BOOKED)
    in_progress(db, vehicles[4], manager, technicians[2], ServiceStatus.BOOKED)

    # Two records left Due long enough to be overdue. One gets dismissed below,
    # so the alerts screen shows both states.
    first_overdue = leave_due(db, vehicles[6], manager, technicians[0], days_ago=21)
    leave_due(db, vehicles[7], manager, technicians[3], days_ago=11)

    # Fresh, still inside the grace period.
    leave_due(db, vehicles[8], manager, technicians[1], days_ago=1)

    dismiss(db, first_overdue, manager)

    # Push two vehicles past their mileage interval. Each opens its own Due
    # cycle on the reading that crosses it - nobody opens those by hand.
    drive_past_interval(db, vehicles[9], manager)
    drive_past_interval(db, vehicles[10], manager)

    vehicle_service.archive_vehicle(db, vehicles[11].id, manager)
    print("Archived one vehicle.")


def complete_cycle(
    db: Session,
    vehicle: Vehicle,
    manager: User,
    technician: User,
    days_ago: int,
) -> None:
    """A full Due -> Completed cycle, then backdated."""
    service = service_service.create_service(
        db, vehicle.id, "Scheduled service and safety inspection", manager
    )
    service_service.assign_technician(db, service.id, technician.id, manager)
    service_service.add_note(
        db, service.id, "Inspection completed, no advisories.", technician
    )

    scheduled = (datetime.now(UTC) - timedelta(days=days_ago)).date()
    move(db, service.id, ServiceStatus.BOOKED, manager, scheduled_date=scheduled)
    move(db, service.id, ServiceStatus.IN_SERVICE, technician)
    move(
        db,
        service.id,
        ServiceStatus.COMPLETED,
        technician,
        completion_odometer=vehicle.current_odometer + 150,
    )

    backdate(db, service.id, days_ago)


def in_progress(
    db: Session,
    vehicle: Vehicle,
    manager: User,
    technician: User,
    target: ServiceStatus,
) -> None:
    service = service_service.create_service(
        db, vehicle.id, "Brake inspection and pad replacement", manager
    )
    service_service.assign_technician(db, service.id, technician.id, manager)

    move(
        db,
        service.id,
        ServiceStatus.BOOKED,
        manager,
        scheduled_date=(datetime.now(UTC) + timedelta(days=3)).date(),
    )
    if target is ServiceStatus.IN_SERVICE:
        move(db, service.id, ServiceStatus.IN_SERVICE, technician)
        service_service.add_note(
            db, service.id, "Front pads worn to 2mm, replacing.", technician
        )


def leave_due(
    db: Session, vehicle: Vehicle, manager: User, technician: User, days_ago: int
):
    """A record that has sat Due, unbooked, for ``days_ago`` days."""
    service = service_service.create_service(
        db, vehicle.id, "Annual service due", manager
    )
    service_service.assign_technician(db, service.id, technician.id, manager)

    # due_since is what the overdue clock counts from, and the service layer
    # always sets it to now - this is the backdating exception again.
    db.execute(
        text("UPDATE service_records SET due_since = :when WHERE id = :id"),
        {"when": datetime.now(UTC) - timedelta(days=days_ago), "id": service.id},
    )
    db.commit()
    return service


def dismiss(db: Session, service, manager: User) -> None:
    from app.services import alert_service, maintenance

    alert_service.dismiss(
        db, service.id, manager, grace_days=7, now=maintenance.utc_now()
    )


def drive_past_interval(db: Session, vehicle: Vehicle, manager: User) -> None:
    """Raise the odometer past the mileage interval, so the vehicle reads Due."""
    from app.schemas.vehicle import VehicleUpdate

    vehicle_service.update_vehicle(
        db,
        vehicle.id,
        VehicleUpdate(
            current_odometer=vehicle.service_baseline_odometer
            + vehicle.service_mileage_interval
            + 400
        ),
        manager,
    )


def move(db: Session, service_id: int, target: ServiceStatus, actor: User, **extra):
    return service_service.transition(
        db, service_id, TransitionRequest(status=target, **extra), actor
    )


def backdate(db: Session, service_id: int, days_ago: int) -> None:
    """Move a completion into the past.

    The only place this script writes data by hand. The service layer cannot
    express it: completing a service is an act in the present, and its rules
    are about now. If the completion rules change, this will not follow them.
    """
    when = datetime.now(UTC) - timedelta(days=days_ago)
    db.execute(
        text(
            "UPDATE service_records SET completed_at = :when, updated_at = :when "
            "WHERE id = :id"
        ),
        {"when": when, "id": service_id},
    )
    db.execute(
        text(
            "UPDATE vehicles SET service_baseline_date = :when "
            "WHERE id = (SELECT vehicle_id FROM service_records WHERE id = :id)"
        ),
        {"when": when.date(), "id": service_id},
    )
    db.commit()


if __name__ == "__main__":
    raise SystemExit(main())
