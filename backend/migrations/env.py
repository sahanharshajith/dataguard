"""Alembic environment: connects migrations to our models and our settings."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

import app.models
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    # Keep the application's own loggers alive when Alembic is run from inside pytest.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# What autogenerate compares the real database against.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to the console instead of running it (`alembic upgrade head --sql`)."""
    url = get_settings().database_url.render_as_string(hide_password=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database."""
    # The test suite hands us a connection it already opened (Alembic cookbook:
    # "sharing a connection with a series of migration commands").
    shared_connection = config.attributes.get("connection")
    if shared_connection is not None:
        do_run_migrations(shared_connection)
        return

    # NullPool: a migration is a short-lived process, so no connection pooling is needed.
    connectable = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()