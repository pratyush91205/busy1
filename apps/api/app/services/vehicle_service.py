"""Vehicle rules.

Everything that decides whether a change is allowed lives here, not in the
route and not in the browser.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import User, Vehicle
from app.repositories import vehicle as vehicle_repository
from app.schemas.pagination import PageParams
from app.schemas.vehicle import SortOrder, VehicleCreate, VehicleSort, VehicleUpdate
from app.services.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


def list_vehicles(
    db: Session,
    *,
    params: PageParams,
    search: str | None = None,
    include_archived: bool = False,
    sort: VehicleSort = VehicleSort.REGISTRATION_NUMBER,
    order: SortOrder = SortOrder.ASC,
) -> tuple[list[Vehicle], int]:
    return vehicle_repository.list_page(
        db,
        params=params,
        search=search,
        include_archived=include_archived,
        sort=sort,
        order=order,
    )


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    """Read one vehicle, archived or not.

    Archiving hides a vehicle from the default list; it does not make its
    history unreachable, which is the whole reason it is a soft delete.
    """
    vehicle = vehicle_repository.get_by_id(db, vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"No vehicle with id {vehicle_id}")
    return vehicle


def create_vehicle(db: Session, payload: VehicleCreate, actor: User) -> Vehicle:
    require_unused_registration(db, payload.registration_number)

    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    logger.info(
        "Vehicle %s created by user %s", vehicle.registration_number, actor.id
    )
    return vehicle


def update_vehicle(
    db: Session, vehicle_id: int, payload: VehicleUpdate, actor: User
) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)
    require_not_archived(vehicle)

    changes = payload.model_dump(exclude_unset=True)

    registration = changes.get("registration_number")
    if registration is not None and registration != vehicle.registration_number:
        require_unused_registration(db, registration)

    odometer = changes.get("current_odometer")
    if odometer is not None:
        require_odometer_not_lower(vehicle, odometer)

    for field, value in changes.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)

    logger.info(
        "Vehicle %s updated by user %s: %s",
        vehicle.registration_number,
        actor.id,
        sorted(changes),
    )
    return vehicle


def archive_vehicle(db: Session, vehicle_id: int, actor: User) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)
    if vehicle.is_archived:
        raise ConflictError(
            f"Vehicle {vehicle.registration_number} is already archived"
        )

    vehicle.is_archived = True
    db.commit()
    db.refresh(vehicle)

    logger.info(
        "Vehicle %s archived by user %s", vehicle.registration_number, actor.id
    )
    return vehicle


def restore_vehicle(db: Session, vehicle_id: int, actor: User) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)
    if not vehicle.is_archived:
        raise ConflictError(f"Vehicle {vehicle.registration_number} is not archived")

    vehicle.is_archived = False
    db.commit()
    db.refresh(vehicle)

    logger.info(
        "Vehicle %s restored by user %s", vehicle.registration_number, actor.id
    )
    return vehicle


# --- rules -------------------------------------------------------------------


def require_unused_registration(db: Session, registration_number: str) -> None:
    if vehicle_repository.get_by_registration(db, registration_number) is not None:
        raise ConflictError(
            f"A vehicle with registration {registration_number} already exists"
        )


def require_not_archived(vehicle: Vehicle) -> None:
    """An archived vehicle is not part of the operating fleet.

    Refusing the edit rather than allowing it is what lets a bulk-odometer CSV
    row for an archived vehicle be rejected with a reason later, instead of
    quietly updating something nobody is driving.
    """
    if vehicle.is_archived:
        raise ConflictError(
            f"Vehicle {vehicle.registration_number} is archived. "
            "Restore it before making changes."
        )


def require_odometer_not_lower(vehicle: Vehicle, reading: int) -> None:
    """current_odometer is monotonically non-decreasing.

    Equal is a no-op success: re-sending yesterday's reading is not an error,
    it just does not move anything.
    """
    if reading < vehicle.current_odometer:
        raise ConflictError(
            f"New reading {reading} is lower than the existing reading "
            f"{vehicle.current_odometer} for vehicle {vehicle.registration_number}"
        )
