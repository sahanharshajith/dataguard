"""Opening the DuckDB warehouse. All timestamps in the warehouse are UTC."""

import os
from pathlib import Path

import duckdb


def connect(path: str | Path | None = None, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Open the warehouse file.

    With no `path`, use the WAREHOUSE_PATH environment variable, falling back to an
    in-memory database (handy for tests and experiments).
    """
    target = str(path) if path is not None else os.environ.get("WAREHOUSE_PATH", ":memory:")
    return duckdb.connect(target, read_only=read_only)