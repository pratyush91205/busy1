"""Create deployment_check and seed its single row.

Revision ID: 0001_deployment_check
Revises:
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_deployment_check"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_LABEL = "fleet-maintenance walking skeleton"


def upgrade() -> None:
    deployment_check = op.create_table(
        "deployment_check",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Seeded here so that a database at head always has the row the read path
    # expects; an empty table is a deployment fault, not a normal state.
    op.bulk_insert(deployment_check, [{"label": SEED_LABEL}])


def downgrade() -> None:
    op.drop_table("deployment_check")
