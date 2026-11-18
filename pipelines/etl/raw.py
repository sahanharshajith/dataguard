"""
RAW layer: load a landing batch into DuckDB with minimal transformation.

* every source column is loaded as text, so bad values still load (finding them is DataGuard's job, not the loader's)
* two metadata columns are added: `_batch_id` and `_loaded_at` (UTC)
* each load REPLACES the table; the CSV files in the landing folder are the history
* the whole load is one transaction: it fully succeeds or leaves the old data untouched
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

TABLES = ("customers", "products", "orders", "order_items", "payments")


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def load_batch_to_raw(
    con: duckdb.DuckDBPyConnection,
    batch_dir: Path | str,
    loaded_at: datetime | None = None,
) -> dict[str, int]:
    """
    Replace every table in schema `raw` with the contents of one batch.

    `loaded_at` defaults to the time in the batch manifest (the `late` scenario fixes a
    past time) or, failing that, to the current time. Returns {table: row_count}.
    """
    batch_dir = Path(batch_dir)
    manifest = json.loads((batch_dir / "batch.json").read_text(encoding="utf-8"))

    if loaded_at is None:
        manifest_time = manifest.get("loaded_at")
        loaded_at = (
            datetime.fromisoformat(manifest_time) if manifest_time else datetime.now(timezone.utc)
        )
    loaded_at = _to_naive_utc(loaded_at)

    counts: dict[str, int] = {}
    con.execute("BEGIN")
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        for table in TABLES:
            # Table names come from the constant above and the path from our own code.
            csv_path = (batch_dir / f"{table}.csv").as_posix().replace("'", "''")
            con.execute(
                f"""
                CREATE OR REPLACE TABLE raw.{table} AS
                SELECT *, ? AS _batch_id, CAST(? AS TIMESTAMP) AS _loaded_at
                FROM read_csv('{csv_path}', header = true, all_varchar = true)
                """,
                [manifest["batch_id"], loaded_at],
            )
            counts[table] = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return counts