"""Request and response shapes for vehicles.

The bounds here duplicate the CHECK constraints on the table on purpose. The
constraint is the guarantee - it holds against any writer. The schema is what
turns a bad value into a readable 422 instead of an IntegrityError.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.text import Collapsed, Stripped


def normalise_registration(value: str) -> str:
    """Collapse whitespace, trim, uppercase.

    The unique index is case-sensitive, so without this ``van001`` and
    ``VAN001`` are two vehicles for the same van. Defined once here because the
    bulk CSV upload has to normalise exactly the same way the API does, or a
    registration that works in the form is unknown in the file.
    """
    return " ".join(value.split()).upper()


class VehicleSort(StrEnum):
    REGISTRATION_NUMBER = "registration_number"
    CURRENT_ODOMETER = "current_odometer"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class VehicleCreate(BaseModel):
    registration_number: Collapsed = Field(min_length=1, max_length=32)
    make: Stripped = Field(min_length=1, max_length=64)
    model: Stripped = Field(min_length=1, max_length=64)
    current_odometer: int = Field(ge=0)
    service_date_interval: int = Field(gt=0, description="Days between services")
    service_mileage_interval: int = Field(gt=0, description="Miles between services")

    @field_validator("registration_number")
    @classmethod
    def normalise(cls, value: str) -> str:
        return normalise_registration(value)


class VehicleUpdate(BaseModel):
    """Every field optional; only what is sent is changed.

    There is no ``is_archived`` here. Archiving goes through its own endpoints
    so that the transition is checked rather than assigned.
    """

    registration_number: Collapsed | None = Field(default=None, min_length=1, max_length=32)
    make: Stripped | None = Field(default=None, min_length=1, max_length=64)
    model: Stripped | None = Field(default=None, min_length=1, max_length=64)
    current_odometer: int | None = Field(default=None, ge=0)
    service_date_interval: int | None = Field(default=None, gt=0)
    service_mileage_interval: int | None = Field(default=None, gt=0)

    @field_validator("registration_number")
    @classmethod
    def normalise(cls, value: str | None) -> str | None:
        return normalise_registration(value) if value is not None else None


class VehicleServiceStatusRead(BaseModel):
    """Why a vehicle is or is not due, not merely whether.

    Derived on read from the intervals and the stored cycle baseline; nothing
    here is persisted.
    """

    is_due: bool
    reason: str | None
    next_due_date: date
    next_due_odometer: int
    has_open_record: bool


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_number: str
    make: str
    model: str
    current_odometer: int
    # Where the current cycle counts from.
    service_baseline_odometer: int
    service_baseline_date: date
    service_date_interval: int
    service_mileage_interval: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    service_status: VehicleServiceStatusRead | None = None

    @classmethod
    def of(cls, vehicle, has_open_record: bool, now: datetime) -> "VehicleRead":
        from app.services import maintenance

        read = cls.model_validate(vehicle)
        status = maintenance.vehicle_service_status(vehicle, has_open_record, now)
        read.service_status = VehicleServiceStatusRead(
            is_due=status.is_due,
            reason=status.reason,
            next_due_date=status.next_due_date,
            next_due_odometer=status.next_due_odometer,
            has_open_record=status.has_open_record,
        )
        return read
