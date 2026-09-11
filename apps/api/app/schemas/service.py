"""Request and response shapes for service records.

The important one is ``ServiceUpdate``. It carries a description and nothing
else - no status, no vehicle_id, no technician list - so an assigned technician
editing a description cannot smuggle a reassignment or a status jump through
the same request. That is enforced by the shape of the schema rather than by
stripping fields at runtime, which is the version that cannot be forgotten.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ServiceStatus
from app.schemas.text import Stripped


class ServiceSort(StrEnum):
    SCHEDULED_DATE = "scheduled_date"
    STATUS = "status"
    UPDATED_AT = "updated_at"


class ServiceCreate(BaseModel):
    """No status field: a new record always starts Due."""

    vehicle_id: int
    description: Stripped = Field(min_length=1, max_length=2000)


class ServiceUpdate(BaseModel):
    description: Stripped = Field(min_length=1, max_length=2000)

    # Anything else the client sends is a mistake worth reporting rather than
    # ignoring - an update carrying "status" is a client that believes it can
    # set one.
    model_config = ConfigDict(extra="forbid")


class TransitionRequest(BaseModel):
    """One endpoint for the whole lifecycle; the target status is data.

    The two extra fields are required by exactly one target each and validated
    against it in the service layer, where the transition table already lives.
    """

    status: ServiceStatus
    scheduled_date: date | None = None
    completion_odometer: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class AssignTechnicianRequest(BaseModel):
    technician_id: int

    model_config = ConfigDict(extra="forbid")


class NoteCreate(BaseModel):
    content: Stripped = Field(min_length=1, max_length=4000)

    model_config = ConfigDict(extra="forbid")


class UserSummary(BaseModel):
    """A user as they appear inside another resource. Never a password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class VehicleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_number: str
    make: str
    model: str


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle: VehicleSummary
    cycle_number: int
    description: str
    status: ServiceStatus
    scheduled_date: date | None
    due_since: datetime | None
    completed_at: datetime | None
    completion_odometer: int | None
    technicians: list[UserSummary]
    created_at: datetime
    updated_at: datetime

    # Derived, never stored. `status` above still holds only the four values;
    # overdue is status Due plus an elapsed grace period.
    is_overdue: bool = False
    overdue_since: datetime | None = None

    @classmethod
    def of(cls, service, grace_days: int, now: datetime) -> "ServiceRead":
        """Build from a record, resolving the derived overdue fields.

        The grace period is passed in rather than read here, so one request
        answers with one consistent value and a test can use a different one.
        """
        from app.services import maintenance

        read = cls.model_validate(service)
        read.overdue_since = maintenance.overdue_threshold(service, grace_days)
        read.is_overdue = maintenance.is_overdue(service, grace_days, now)
        return read


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    author: UserSummary
    created_at: datetime


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    old_value: str | None
    new_value: str | None
    event_metadata: dict | None
    # Null means the system acted rather than a person.
    actor: UserSummary | None
    created_at: datetime
