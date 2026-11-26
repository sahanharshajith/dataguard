# Data pipelines

The demo platform monitors an e-commerce warehouse in DuckDB: `/data/warehouse/ecommerce.duckdb`
on a shared Docker volume, with three schemas.

| Layer | Schema | Contents |
|---|---|---|
| RAW | `raw` | The source files as text plus `_batch_id` and `_loaded_at`. Each load replaces the table; the CSVs in `data/landing/` are the history |
| STAGING | `staging` | Typed (`TRY_CAST`), standardized, de-duplicated. Invalid rows are kept, not rejected |
| ANALYTICS | `analytics` | `fct_orders` (with an `is_valid` flag), `dim_customers`, `dim_products`, `daily_sales` |

## Scenarios

Generated deterministically by `python -m pipelines.generator --scenario <name>`, or from the
Airflow UI (DAG `ecommerce_generate_batch`).

| Scenario | What it contains | Detected by |
|---|---|---|
| `clean` | Nothing wrong | (control) |
| `dirty` | 25 duplicate order ids, 40 missing customer ids, 30 invalid totals, 20 total mismatches, 35 orphan customers, 15 unparseable totals, 15 unparseable dates | quality rules |
| `schema_drift` | An unexpected `coupon_code` column in `orders` | schema change detection |
| `volume_drop` | 600 orders instead of 5,000 | volume anomaly detection |
| `late` | Loaded with a timestamp 3 days in the past | freshness monitoring |

Each batch's `batch.json` records the ground truth (what was planted, row counts).

## DAGs

`ecommerce_generate_batch` → `ecommerce_ingestion` → `ecommerce_transform`. Warehouse writes use
the one-slot Airflow pool `warehouse` because a DuckDB file has a single writer.

## Running the tests

`pytest` runs the generator, RAW, STAGING, and ANALYTICS tests on in-memory DuckDB; no Docker needed.