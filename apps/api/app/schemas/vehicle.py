"""Request and response shapes for vehicles.

The bounds here duplicate the CHECK constraints on the table on purpose. The
constraint is the guarantee - it holds against any writer. The schema is what
turns a bad value into a readable 422 instead of an IntegrityError.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalise_registration(value: str) -> str:
    """Trimmed uppercase.

    The unique index is case-sensitive, so without this ``van001`` and
    ``VAN001`` are two vehicles. Normalising on the way in makes the existing
    index sufficient and stores the form a depot would actually write.
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
    registration_number: str = Field(min_length=1, max_length=32)
    make: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=64)
    current_odometer: int = Field(ge=0)
    service_date_interval: int = Field(gt=0, description="Days between services")
    service_mileage_interval: int = Field(gt=0, description="Miles between services")

    @field_validator("registration_number")
    @classmethod
    def normalise(cls, value: str) -> str:
        return normalise_registration(value)

    @field_validator("make", "model")
    @classmethod
    def strip(cls, value: str) -> str:
        return value.strip()


class VehicleUpdate(BaseModel):
    """Every field optional; only what is sent is changed.

    There is no ``is_archived`` here. Archiving goes through its own endpoints
    so that the transition is checked rather than assigned.
    """

    registration_number: str | None = Field(default=None, min_length=1, max_length=32)
    make: str | None = Field(default=None, min_length=1, max_length=64)
    model: str | None = Field(default=None, min_length=1, max_length=64)
    current_odometer: int | None = Field(default=None, ge=0)
    service_date_interval: int | None = Field(default=None, gt=0)
    service_mileage_interval: int | None = Field(default=None, gt=0)

    @field_validator("registration_number")
    @classmethod
    def normalise(cls, value: str | None) -> str | None:
        return normalise_registration(value) if value is not None else None

    @field_validator("make", "model")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_number: str
    make: str
    model: str
    current_odometer: int
    service_date_interval: int
    service_mileage_interval: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
