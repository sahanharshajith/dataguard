
"""STAGING layer: typed, cleaned, de-duplicated tables built from RAW."""

from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).parent / "sql" / "staging"

TABLES = [
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
]


def build_staging(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Build every table of the staging schema from the raw schema."""

    # Create the staging schema if it doesn't exist.
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")

    # Store the row counts for every table.
    row_counts = {}

    # Execute each SQL file.
    for table in TABLES:

        sql_file = SQL_DIR / f"{table}.sql"

        sql = sql_file.read_text(encoding="utf-8")

        con.execute(sql)

        # Count the rows in the newly created table.
        count = con.execute(
            f"SELECT COUNT(*) FROM staging.{table}"
        ).fetchone()[0]

        row_counts[table] = count

    # Return the row counts.
    return row_counts
