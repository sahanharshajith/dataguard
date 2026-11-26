"""DAG 2 of 3: load one landing batch into the RAW layer, then start the transform DAG."""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import Param, dag, task


@dag(
    dag_id="ecommerce_ingestion",
    description="Landing CSV files -> raw.* tables in the DuckDB warehouse.",
    schedule=None,  # started by ecommerce_generate_batch, or manually
    start_date=datetime(2026, 1, 1),
    catchup=False,
    is_paused_upon_creation=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=10)},
    params={
        "batch_id": Param(
            "",
            type="string",
            description="Folder name under the landing zone. Leave empty to load the newest batch.",
        ),
    },
    tags=["dataguard", "ecommerce"],
)
def ecommerce_ingestion():
    # pool="warehouse" has one slot: only one task may write to the DuckDB file at a time.
    @task(pool="warehouse")
    def load_raw(params: dict) -> str:
        import os
        from pathlib import Path

        from pipelines.etl.raw import load_batch_to_raw
        from pipelines.etl.warehouse import connect

        landing = Path(os.environ.get("LANDING_PATH", "/data/landing"))

        batch_id = params["batch_id"]
        if batch_id:
            if Path(batch_id).name != batch_id:  # no path tricks like ../..
                raise ValueError(f"batch_id must be a plain folder name, got {batch_id!r}")
        else:
            batches = [p for p in landing.iterdir() if (p / "batch.json").exists()]
            if not batches:
                raise FileNotFoundError(f"No batches found in {landing}")
            batch_id = max(batches, key=lambda p: p.stat().st_mtime).name

        con = connect()
        try:
            counts = load_batch_to_raw(con, landing / batch_id)
        finally:
            con.close()
        print(f"Loaded batch {batch_id}: {counts}")
        return batch_id

    trigger_transform = TriggerDagRunOperator(
        task_id="trigger_transform",
        trigger_dag_id="ecommerce_transform",
        wait_for_completion=False,
    )

    load_raw() >> trigger_transform


ecommerce_ingestion()