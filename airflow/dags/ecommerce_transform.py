"""DAG 3 of 3: build the STAGING layer, then the ANALYTICS layer, from RAW."""

from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="ecommerce_transform",
    description="raw.* -> staging.* -> analytics.* in the DuckDB warehouse.",
    schedule=None,  # started by ecommerce_ingestion, or manually
    start_date=datetime(2026, 1, 1),
    catchup=False,
    is_paused_upon_creation=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=10)},
    tags=["dataguard", "ecommerce"],
)
def ecommerce_transform():
    @task(pool="warehouse")
    def staging() -> dict:
        from pipelines.etl.staging import build_staging
        from pipelines.etl.warehouse import connect

        con = connect()
        try:
            counts = build_staging(con)
        finally:
            con.close()
        print(f"Staging built: {counts}")
        return counts

    @task(pool="warehouse")
    def analytics() -> dict:
        from pipelines.etl.analytics import build_analytics
        from pipelines.etl.warehouse import connect

        con = connect()
        try:
            counts = build_analytics(con)
        finally:
            con.close()
        print(f"Analytics built: {counts}")
        return counts

    staging() >> analytics()


ecommerce_transform()
