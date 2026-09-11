"""The migration chain applies cleanly and reverses cleanly.

Worth more than its size: this is the moment to prove the chain is reversible,
while there is still exactly one migration in it.
"""

from __future__ import annotations

from alembic import command
from sqlalchemy import Engine, inspect, text

from tests.conftest import alembic_config

SEED_LABEL = "fleet-maintenance walking skeleton"


def table_exists(engine: Engine, name: str) -> bool:
    return inspect(engine).has_table(name)


def seeded_labels(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT label FROM deployment_check"))
        return [row[0] for row in rows]


def applied_revisions(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT version_num FROM alembic_version"))
        return [row[0] for row in rows]


def test_upgrade_and_downgrade_round_trip(
    migrated_engine: Engine, test_database_url: str
) -> None:
    config = alembic_config(test_database_url)

    # The session fixture already migrated to head.
    assert table_exists(migrated_engine, "deployment_check")
    assert seeded_labels(migrated_engine) == [SEED_LABEL]
    assert applied_revisions(migrated_engine) == ["0001_deployment_check"]

    command.downgrade(config, "base")
    assert not table_exists(migrated_engine, "deployment_check")
    # Alembic keeps its own bookkeeping table; what matters is that it records
    # no applied revision.
    assert applied_revisions(migrated_engine) == []

    # Leave the database at head for the rest of the session.
    command.upgrade(config, "head")
    assert table_exists(migrated_engine, "deployment_check")
    assert seeded_labels(migrated_engine) == [SEED_LABEL]
