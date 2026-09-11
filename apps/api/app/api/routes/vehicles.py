"""Vehicle routes.

Thin on purpose: resolve dependencies, call one service function, return. Every
rule and every rejection lives in ``vehicle_service``, and the domain errors it
raises are turned into responses by the handler in ``app.main``.

There is no DELETE. Archive is the only removal, which is what keeps a
vehicle's service history readable.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, PageQuery, require_role
from app.models import User, UserRole
from app.schemas.pagination import Page
from app.schemas.vehicle import (
    SortOrder,
    VehicleCreate,
    VehicleRead,
    VehicleSort,
    VehicleUpdate,
)
from app.services import maintenance, vehicle_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

# Reads are open to any signed-in user: a technician needs to know which
# vehicle a job is on. Every mutation is a manager's.
Manager = Annotated[User, Depends(require_role(UserRole.FLEET_MANAGER))]


def read_of(db, vehicle) -> VehicleRead:
    """Serialise one vehicle with its derived service status resolved."""
    return VehicleRead.of(
        vehicle,
        bool(vehicle_service.open_record_vehicle_ids(db, [vehicle])),
        maintenance.utc_now(),
    )


@router.get("", response_model=Page[VehicleRead])
def list_vehicles(
    db: DbSession,
    _: CurrentUser,
    params: PageQuery,
    search: Annotated[str | None, Query(max_length=100)] = None,
    include_archived: bool = False,
    sort: VehicleSort = VehicleSort.REGISTRATION_NUMBER,
    order: SortOrder = SortOrder.ASC,
    due: bool | None = None,
) -> Page[VehicleRead]:
    now = maintenance.utc_now()

    vehicles, total = vehicle_service.list_vehicles(
        db,
        params=params,
        search=search,
        include_archived=include_archived,
        sort=sort,
        order=order,
        due=due,
        today=now.date(),
    )

    # One query for the whole page, not one per vehicle.
    open_records = vehicle_service.open_record_vehicle_ids(db, vehicles)

    return Page[VehicleRead].build(
        [
            VehicleRead.of(vehicle, vehicle.id in open_records, now)
            for vehicle in vehicles
        ],
        total,
        params,
    )


@router.get("/{vehicle_id}", response_model=VehicleRead)
def read_vehicle(vehicle_id: int, db: DbSession, _: CurrentUser) -> VehicleRead:
    vehicle = vehicle_service.get_vehicle(db, vehicle_id)
    return VehicleRead.of(
        vehicle,
        bool(vehicle_service.open_record_vehicle_ids(db, [vehicle])),
        maintenance.utc_now(),
    )


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate, db: DbSession, actor: Manager
) -> VehicleRead:
    return read_of(db, vehicle_service.create_vehicle(db, payload, actor))


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: int, payload: VehicleUpdate, db: DbSession, actor: Manager
) -> VehicleRead:
    return read_of(db, vehicle_service.update_vehicle(db, vehicle_id, payload, actor))


@router.post("/{vehicle_id}/archive", response_model=VehicleRead)
def archive_vehicle(vehicle_id: int, db: DbSession, actor: Manager) -> VehicleRead:
    return read_of(db, vehicle_service.archive_vehicle(db, vehicle_id, actor))


@router.post("/{vehicle_id}/restore", response_model=VehicleRead)
def restore_vehicle(vehicle_id: int, db: DbSession, actor: Manager) -> VehicleRead:
    return read_of(db, vehicle_service.restore_vehicle(db, vehicle_id, actor))
