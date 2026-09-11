"""Alembic environment.

The connection URL comes from the environment, never from alembic.ini. Callers
(the tests, in particular) may override it by setting ``sqlalchemy.url`` on the
Alembic config object.
"""

from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.db.session import build_engine
from app.models import deployment_check  # noqa: F401  registers the table
from app.models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().migration_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = build_engine(database_url())
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
