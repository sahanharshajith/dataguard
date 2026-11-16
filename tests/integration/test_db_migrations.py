"""The migrations and the models must describe the same database."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

import app.models
from app.db.base import Base

pytestmark = pytest.mark.integration


def test_migrations_create_exactly_the_tables_the_models_define(engine):
    actual = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert actual == set(Base.metadata.tables)


def test_models_and_migrations_are_in_sync(engine):
    # If this fails, a model was changed without generating a migration (or vice versa).
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == [], f"Models and migrations disagree: {differences}"