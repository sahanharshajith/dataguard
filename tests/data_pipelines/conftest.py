from datetime import date

import duckdb
import pytest

from pipelines.etl.raw import load_batch_to_raw
from pipelines.generator.generate import Scenario, generate_batch

AS_OF = date(2026, 11, 16)


@pytest.fixture(scope="session")
def batches(tmp_path_factory):
    """One generated batch directory per scenario, created once per test session."""
    root = tmp_path_factory.mktemp("landing")
    return {scenario: generate_batch(scenario, root, AS_OF) for scenario in Scenario}


@pytest.fixture
def raw_con(batches):
    """Factory: `raw_con(Scenario.DIRTY)` returns a fresh in-memory warehouse with RAW loaded."""
    connections = []

    def _make(scenario):
        con = duckdb.connect()
        load_batch_to_raw(con, batches[scenario])
        connections.append(con)
        return con

    yield _make
    for con in connections:
        con.close()