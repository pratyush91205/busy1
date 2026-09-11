"""The migration chain applies cleanly and reverses cleanly.

Kept honest at every revision: the chain is exercised end to end while it is
still short enough to reason about.
"""

from __future__ import annotations

from alembic import command
from sqlalchemy import Engine, inspect, text

from tests.conftest import alembic_config

DOMAIN_TABLES = {
    "users",
    "vehicles",
    "service_records",
    "service_technicians",
    "service_notes",
    "audit_events",
    "overdue_alert_dismissals",
}
SKELETON_SEED_LABEL = "fleet-maintenance walking skeleton"


def table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def applied_revisions(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT version_num FROM alembic_version"))
        return [row[0] for row in rows]


def test_upgrade_and_downgrade_round_trip(
    migrated_engine: Engine, test_database_url: str
) -> None:
    config = alembic_config(test_database_url)

    # The session fixture already migrated to head.
    assert DOMAIN_TABLES <= table_names(migrated_engine)
    assert applied_revisions(migrated_engine) == ["0003_service_cycle_baseline"]

    command.downgrade(config, "base")
    remaining = table_names(migrated_engine)
    assert not (DOMAIN_TABLES & remaining)
    # 0002's downgrade recreates the skeleton table so that 0001 stays truthful;
    # 0001's downgrade then drops it.
    assert "deployment_check" not in remaining
    assert applied_revisions(migrated_engine) == []

    # Leave the database at head for the rest of the session.
    command.upgrade(config, "head")
    assert DOMAIN_TABLES <= table_names(migrated_engine)


def test_intermediate_revision_restores_the_skeleton_table(
    migrated_engine: Engine, test_database_url: str
) -> None:
    """Downgrading one step must land on a database 0001 would recognise."""
    config = alembic_config(test_database_url)

    command.downgrade(config, "0001_deployment_check")
    tables = table_names(migrated_engine)
    assert "deployment_check" in tables
    assert not (DOMAIN_TABLES & tables)

    with migrated_engine.connect() as connection:
        labels = [
            row[0] for row in connection.execute(text("SELECT label FROM deployment_check"))
        ]
    assert labels == [SKELETON_SEED_LABEL]

    command.upgrade(config, "head")
    assert "deployment_check" not in table_names(migrated_engine)
