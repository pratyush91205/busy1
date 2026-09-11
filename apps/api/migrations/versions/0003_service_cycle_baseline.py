"""Store the point the current service cycle counts from.

"Is this vehicle due" is two comparisons, and each needs a fixed point to
measure against:

* Mileage. ``current_odometer`` cannot be its own baseline - it moves, so
  "due at current + interval" is a target that runs away as the van is driven
  and is never reached. Zero is worse: a used van joining the fleet with 80,000
  miles on the clock would be due the day it was added.
* Date. This one could be derived - the last completed service, falling back to
  the vehicle's creation - but that needs a lateral join to the newest
  completed record on every read, and on every row of a filtered fleet list.

Storing both turns due-ness into a single-table predicate that any index can
serve, and keeps the two halves symmetric. They are set when the vehicle is
created and again each time a service completes, which is the counter reset the
brief asks for.

Backfilled for existing rows from the values they do have. The columns go in
nullable, are filled, then made NOT NULL.

Revision ID: 0003_service_cycle_baseline
Revises: 0002_domain_schema
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_service_cycle_baseline"
down_revision: str | None = "0002_domain_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vehicles",
        sa.Column("service_baseline_odometer", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vehicles",
        sa.Column("service_baseline_date", sa.Date(), nullable=True),
    )

    # Existing vehicles have no recorded cycle start. The current reading and
    # the creation date are the honest answers: they become due one full
    # interval from where they are now.
    op.execute(
        """
        UPDATE vehicles
        SET service_baseline_odometer = COALESCE(
                service_baseline_odometer, current_odometer
            ),
            service_baseline_date = COALESCE(
                service_baseline_date, created_at::date
            )
        """
    )

    op.alter_column("vehicles", "service_baseline_odometer", nullable=False)
    op.alter_column("vehicles", "service_baseline_date", nullable=False)

    op.create_check_constraint(
        "ck_vehicles_baseline_odometer_non_negative",
        "vehicles",
        "service_baseline_odometer >= 0",
    )

    # The overdue list is "status = due, ordered by how long". Spec 02 already
    # indexes each column separately; this is the composite that query wants.
    op.create_index(
        "ix_service_records_status_due_since",
        "service_records",
        ["status", "due_since"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_records_status_due_since", table_name="service_records")
    op.drop_constraint(
        "ck_vehicles_baseline_odometer_non_negative", "vehicles", type_="check"
    )
    op.drop_column("vehicles", "service_baseline_date")
    op.drop_column("vehicles", "service_baseline_odometer")
