"""DAG 1 of 3: generate one batch of sample data, then start the ingestion DAG."""

from datetime import date, datetime, timedelta, timezone

from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import Param, dag, task

from pipelines.generator.generate import Scenario


@dag(
    dag_id="ecommerce_generate_batch",
    description="Write one batch of e-commerce CSV files to the landing zone.",
    schedule=None,  # manual: trigger it from the Airflow UI and pick a scenario
    start_date=datetime(2026, 1, 1),
    catchup=False,
    is_paused_upon_creation=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=10)},
    params={
        "scenario": Param(
            "clean",
            type="string",
            enum=[scenario.value for scenario in Scenario],
            description="Which data problems to plant (clean = none).",
        ),
        "as_of": Param(
            "",
            type="string",
            description="Batch date, YYYY-MM-DD. Leave empty for today (UTC).",
        ),
    },
    tags=["dataguard", "ecommerce"],
)
def ecommerce_generate_batch():
    @task
    def generate(params: dict) -> str:
        # Imported inside the task so parsing this file stays fast.
        import os
        from pathlib import Path

        from pipelines.generator.generate import generate_batch

        as_of = (
            date.fromisoformat(params["as_of"])
            if params["as_of"]
            else datetime.now(timezone.utc).date()
        )
        landing = Path(os.environ.get("LANDING_PATH", "/data/landing"))
        batch_dir = generate_batch(Scenario(params["scenario"]), landing, as_of)
        print(f"Generated {batch_dir}")
        return batch_dir.name

    trigger_ingestion = TriggerDagRunOperator(
        task_id="trigger_ingestion",
        trigger_dag_id="ecommerce_ingestion",
        conf={"batch_id": "{{ ti.xcom_pull(task_ids='generate') }}"},
        wait_for_completion=False,
    )

    generate() >> trigger_ingestion


ecommerce_generate_batch()