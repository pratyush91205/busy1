"""Bulk odometer upload: one CSV, one result per row.

This module deliberately breaks the pattern the rest of the codebase follows.
Everywhere else a request is one transaction that commits or rolls back whole.
Here it must not be: a depot uploads fifty readings, one of them is a typo, and
discarding the other forty-nine because of it would be useless. So each row is
validated and committed on its own, and one failure has no effect on any other.

The one whole-file rejection is a missing or malformed header. That does not
mean a row is wrong; it means the file is not the thing this endpoint takes, so
nothing in it can be trusted.

The rules themselves are not reimplemented here. Whether a reading may be
applied is ``vehicle_service``'s question, already written and already tested;
this module parses, dispatches and reports.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import vehicle as vehicle_repository
from app.schemas.vehicle import normalise_registration
from app.services import due_cycles, maintenance
from app.services.errors import ConflictError, DomainError

logger = logging.getLogger(__name__)

REGISTRATION_COLUMN = "registration_number"
ODOMETER_COLUMN = "odometer"
REQUIRED_HEADER = (REGISTRATION_COLUMN, ODOMETER_COLUMN)

# A CSV is read into memory to be parsed, so both are capped. An unbounded
# upload is a way to take the process down, not a feature.
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5_000


class RowStatus(StrEnum):
    SUCCESS = "success"
    REJECTED = "rejected"


class MalformedCsvError(DomainError):
    """The file is not a readable odometer CSV. 422, whole upload."""

    status_code = 422


@dataclass
class RowResult:
    # The row number a person would count in their spreadsheet: 1-based over
    # the data rows, not counting the header.
    row: int
    registration_number: str | None
    status: RowStatus
    message: str
    previous_odometer: int | None = None
    new_odometer: int | None = None


@dataclass
class UploadReport:
    results: list[RowResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for row in self.results if row.status is RowStatus.SUCCESS)

    @property
    def failed(self) -> int:
        return self.total - self.succeeded


def process(db: Session, content: bytes, actor: User) -> UploadReport:
    """Apply every valid row, report on all of them."""
    reader = build_reader(content)
    report = UploadReport()
    seen: dict[str, int] = {}

    for index, raw in enumerate(reader, start=1):
        if is_blank(raw):
            # A trailing newline is not a failed row.
            continue

        report.results.append(apply_row(db, index, raw, seen))

    logger.info(
        "Odometer upload by user %s: %s rows, %s applied, %s rejected",
        actor.id,
        report.total,
        report.succeeded,
        report.failed,
    )
    return report


def build_reader(content: bytes) -> csv.DictReader:
    """Parse the bytes, or refuse the whole file.

    The header check is strict: an endpoint that guesses at column names will
    one day guess wrong and silently write the wrong column.
    """
    if len(content) > MAX_BYTES:
        raise MalformedCsvError(
            f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB."
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MalformedCsvError(
            "The file is not UTF-8 text. Export it as CSV rather than a "
            "spreadsheet file."
        ) from exc

    # Counted before anything is applied. Checking the cap while iterating
    # would mean the first MAX_ROWS rows were already written before the file
    # was refused - which is both slow and the wrong answer.
    if text.count("\n") > MAX_ROWS:
        raise MalformedCsvError(
            f"The file has more than {MAX_ROWS} rows. Split it and upload the "
            "parts separately."
        )

    reader = csv.DictReader(io.StringIO(text))
    header = tuple(name.strip().lower() for name in (reader.fieldnames or ()))

    if header != REQUIRED_HEADER:
        raise MalformedCsvError(
            "The first line must be exactly "
            f"'{','.join(REQUIRED_HEADER)}'. Found: "
            f"'{','.join(reader.fieldnames or []) or '(empty file)'}'."
        )

    return reader


def apply_row(
    db: Session, row_number: int, raw: dict, seen: dict[str, int]
) -> RowResult:
    """Validate and apply one row. Never raises; always reports."""
    registration = normalise_registration(str(raw.get(REGISTRATION_COLUMN) or ""))

    if not registration:
        return rejected(row_number, None, "Registration number is missing.")

    if registration in seen:
        return rejected(
            row_number,
            registration,
            f"{registration} already appears on row {seen[registration]}. "
            "Only the first reading for a vehicle is applied.",
        )
    seen[registration] = row_number

    reading = parse_odometer(raw.get(ODOMETER_COLUMN))
    if reading is None:
        return rejected(
            row_number,
            registration,
            f"Odometer '{raw.get(ODOMETER_COLUMN)}' is not a whole number of "
            "miles at or above zero.",
        )

    vehicle = vehicle_repository.get_by_registration(db, registration)
    if vehicle is None:
        return rejected(row_number, registration, f"No vehicle {registration}.")

    previous = vehicle.current_odometer

    # The rules live in vehicle_service and are already tested there. Reusing
    # them is what stops the CSV path and the API path disagreeing about what
    # a valid reading is.
    from app.services import vehicle_service

    try:
        vehicle_service.require_not_archived(vehicle)
        vehicle_service.require_odometer_not_lower(vehicle, reading)
    except ConflictError as exc:
        # One bad row is rolled back on its own; the rows before it are already
        # committed and the rows after it are untouched.
        db.rollback()
        return rejected(row_number, registration, exc.message)

    if reading == previous:
        # An accepted no-op, not an error. Re-sending yesterday's reading is
        # also what makes a failed upload safe to retry.
        return RowResult(
            row=row_number,
            registration_number=registration,
            status=RowStatus.SUCCESS,
            message=f"Already at {previous}; nothing to change.",
            previous_odometer=previous,
            new_odometer=previous,
        )

    vehicle.current_odometer = reading
    try:
        # A reading that crosses the mileage interval opens the vehicle's next
        # cycle in this row's commit: the reading and the Due record it caused
        # land together or not at all.
        opened = due_cycles.open_cycle_if_due(db, vehicle, maintenance.utc_now())
        # Committed per row on purpose: see the module docstring. A reading is
        # not a service, so service_baseline_odometer is untouched and this
        # cannot make a vehicle stop being due.
        db.commit()
    except IntegrityError:
        db.rollback()
        return rejected(
            row_number,
            registration,
            "Another change to this vehicle landed at the same moment. "
            "Upload this row again.",
        )

    message = f"Updated to {reading}."
    if opened is not None:
        message += f" Now due for service - cycle {opened.cycle_number} opened."

    return RowResult(
        row=row_number,
        registration_number=registration,
        status=RowStatus.SUCCESS,
        message=message,
        previous_odometer=previous,
        new_odometer=reading,
    )


def parse_odometer(value: object) -> int | None:
    """A whole number of miles at or above zero, or None."""
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        reading = int(text)
    except ValueError:
        return None
    return reading if reading >= 0 else None


def is_blank(raw: dict) -> bool:
    return not any(str(value or "").strip() for value in raw.values())


def rejected(row: int, registration: str | None, message: str) -> RowResult:
    return RowResult(
        row=row,
        registration_number=registration,
        status=RowStatus.REJECTED,
        message=message,
    )
