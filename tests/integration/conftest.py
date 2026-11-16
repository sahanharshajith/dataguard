"""Fixtures for tests that need a real PostgreSQL database.

These tests are opt-in: set TEST_DATABASE_URL to a database whose name ends in `_test`.
At the start of each test session that database is dropped and recreated, then built by
running the real Alembic migrations, so the migrations are tested too. Each test runs
inside a transaction that is rolled back afterwards, so tests cannot affect each other.
"""

import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "backend" / "migrations"
SAFE_DATABASE_NAME = re.compile(r"^[a-z0-9_]+_test$")


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url_text = os.environ.get("TEST_DATABASE_URL")
    if not url_text:
        pytest.skip("TEST_DATABASE_URL is not set (integration tests need a real PostgreSQL)")

    url = make_url(url_text)
    # Safety: this fixture DROPS the database, so refuse anything that is not clearly a test DB.
    if not url.database or not SAFE_DATABASE_NAME.match(url.database):
        pytest.fail("TEST_DATABASE_URL must point at a database whose name ends in '_test'")

    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()

    test_engine = create_engine(url)
    config = alembic_config()
    with test_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back at the end of the test."""
    connection = engine.connect()
    transaction = connection.begin()
    # create_savepoint: even if the code under test calls commit(), only a savepoint is released.
    db_session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield db_session
    db_session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def assert_rejected(session: Session) -> Callable[[str, Callable[[], object]], None]:
    """Assert that PostgreSQL itself rejects a change, naming the constraint that fired."""

    def _assert_rejected(constraint: str, action: Callable[[], object]) -> None:
        # The savepoint keeps the failed statement from poisoning the rest of the test.
        with pytest.raises(IntegrityError) as error:
            with session.begin_nested():
                action()
                session.flush()
        assert error.value.orig.diag.constraint_name == constraint

    return _assert_rejected