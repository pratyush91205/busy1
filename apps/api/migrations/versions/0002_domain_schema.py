"""Create the domain schema and drop the walking skeleton table.

Revision ID: 0002_domain_schema
Revises: 0001_deployment_check
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_domain_schema"
down_revision: str | None = "0001_deployment_check"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLES = ("fleet_manager", "technician")
SERVICE_STATUSES = ("due", "booked", "in_service", "completed")
AUDIT_EVENT_TYPES = (
    "service_created",
    "status_changed",
    "technician_assigned",
    "technician_unassigned",
    "note_added",
)

SKELETON_SEED_LABEL = "fleet-maintenance walking skeleton"


def in_list(column: str, values: Sequence[str]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(in_list("role", USER_ROLES), name="ck_users_role"),
    )

    op.create_table(
        "vehicles",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("registration_number", sa.Text(), nullable=False),
        sa.Column("make", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("current_odometer", sa.Integer(), nullable=False),
        sa.Column("service_date_interval", sa.Integer(), nullable=False),
        sa.Column("service_mileage_interval", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_vehicles"),
        sa.UniqueConstraint("registration_number", name="uq_vehicles_registration_number"),
        sa.CheckConstraint("current_odometer >= 0", name="ck_vehicles_odometer_non_negative"),
        sa.CheckConstraint("service_date_interval > 0", name="ck_vehicles_date_interval_positive"),
        sa.CheckConstraint(
            "service_mileage_interval > 0", name="ck_vehicles_mileage_interval_positive"
        ),
    )
    op.create_index("ix_vehicles_is_archived", "vehicles", ["is_archived"])
    op.execute(
        "COMMENT ON COLUMN vehicles.service_date_interval IS "
        "'Service interval in days since the last completed service'"
    )
    op.execute(
        "COMMENT ON COLUMN vehicles.service_mileage_interval IS "
        "'Service interval in miles since the last completed service odometer'"
    )
    op.execute(
        "COMMENT ON COLUMN vehicles.current_odometer IS "
        "'Most recently recorded reading; the source of truth for odometer validation'"
    )

    op.create_table(
        "service_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("vehicle_id", sa.BigInteger(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("due_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_odometer", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_service_records"),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_service_records_vehicle_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "vehicle_id", "cycle_number", name="uq_service_records_vehicle_cycle"
        ),
        sa.CheckConstraint(in_list("status", SERVICE_STATUSES), name="ck_service_records_status"),
        sa.CheckConstraint("cycle_number > 0", name="ck_service_records_cycle_number_positive"),
        sa.CheckConstraint(
            "char_length(btrim(description)) > 0",
            name="ck_service_records_description_not_blank",
        ),
        sa.CheckConstraint(
            "completion_odometer IS NULL OR completion_odometer >= 0",
            name="ck_service_records_completion_odometer_non_negative",
        ),
    )
    op.create_index("ix_service_records_vehicle_id", "service_records", ["vehicle_id"])
    op.create_index("ix_service_records_status", "service_records", ["status"])
    op.create_index("ix_service_records_scheduled_date", "service_records", ["scheduled_date"])
    op.create_index("ix_service_records_updated_at", "service_records", ["updated_at"])
    op.create_index("ix_service_records_due_since", "service_records", ["due_since"])
    op.execute(
        "COMMENT ON COLUMN service_records.cycle_number IS "
        "'Service cycle identifier, numbered from 1 per vehicle'"
    )
    op.execute(
        "COMMENT ON COLUMN service_records.due_since IS "
        "'When this cycle first became Due; the overdue grace period counts from here'"
    )

    op.create_table(
        "service_technicians",
        sa.Column("service_id", sa.BigInteger(), nullable=False),
        sa.Column("technician_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("service_id", "technician_id", name="pk_service_technicians"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["service_records.id"],
            name="fk_service_technicians_service_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technician_id"],
            ["users.id"],
            name="fk_service_technicians_technician_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_service_technicians_technician_id", "service_technicians", ["technician_id"]
    )

    op.create_table(
        "service_notes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("service_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_service_notes"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["service_records.id"],
            name="fk_service_notes_service_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_service_notes_author_id", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) > 0", name="ck_service_notes_content_not_blank"
        ),
    )
    op.create_index("ix_service_notes_service_id", "service_notes", ["service_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("service_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["service_records.id"],
            name="fk_audit_events_service_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_events_actor_id", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            in_list("event_type", AUDIT_EVENT_TYPES), name="ck_audit_events_event_type"
        ),
    )
    op.create_index(
        "ix_audit_events_service_id_created_at", "audit_events", ["service_id", "created_at"]
    )
    op.execute(
        "COMMENT ON COLUMN audit_events.actor_id IS "
        "'Null means the system acted rather than a user'"
    )

    # Append-only, enforced by the database rather than by the absence of an
    # endpoint. This holds for a Fleet Manager and for a psql prompt alike.
    # Row triggers do not fire on TRUNCATE, which is how the tests clean up.
    op.execute(
        """
        CREATE FUNCTION audit_events_reject_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_events is append-only: % is not permitted', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_update
        BEFORE UPDATE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_reject_change();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_delete
        BEFORE DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_reject_change();
        """
    )

    op.create_table(
        "overdue_alert_dismissals",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("service_id", sa.BigInteger(), nullable=False),
        sa.Column("dismissed_by", sa.BigInteger(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_overdue_alert_dismissals"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["service_records.id"],
            name="fk_overdue_alert_dismissals_service_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dismissed_by"],
            ["users.id"],
            name="fk_overdue_alert_dismissals_dismissed_by",
            ondelete="RESTRICT",
        ),
        # One dismissal per service record, and one service record per cycle,
        # so a dismissal can never suppress the next cycle's alert.
        sa.UniqueConstraint("service_id", name="uq_overdue_alert_dismissals_service_id"),
    )

    # The walking skeleton's table has served its purpose: the read path it
    # proved is now covered by real domain tables.
    op.drop_table("deployment_check")


def downgrade() -> None:
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
    op.bulk_insert(deployment_check, [{"label": SKELETON_SEED_LABEL}])

    op.drop_table("overdue_alert_dismissals")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events")
    op.drop_table("audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_reject_change()")
    op.drop_table("service_notes")
    op.drop_table("service_technicians")
    op.drop_table("service_records")
    op.drop_table("vehicles")
    op.drop_table("users")
