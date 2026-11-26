
"""ANALYTICS layer: business-ready tables built from STAGING."""

from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).parent / "sql" / "analytics"

# Execution order matters because the dimension tables
# and daily_sales depend on fct_orders.
TABLES = [
    "fct_orders",
    "dim_customers",
    "dim_products",
    "daily_sales",
]


def build_analytics(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Build every table of the analytics schema from staging."""

    # Create analytics schema.
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    # Prepare a dictionary for row counts.
    row_counts = {}

    # Execute SQL files in dependency order.
    for table in TABLES:

        sql_file = SQL_DIR / f"{table}.sql"

        sql = sql_file.read_text(encoding="utf-8")

        con.execute(sql)

        # Count rows in the created table.
        count = con.execute(
            f"SELECT COUNT(*) FROM analytics.{table}"
        ).fetchone()[0]

        row_counts[table] = count

    # Return all row counts.
    return row_counts
