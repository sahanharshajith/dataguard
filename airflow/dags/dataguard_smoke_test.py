"""
Smoke-test DAG: proves Airflow can load, schedule, and run DataGuard tasks.

It touches no data. Delete or keep it.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="dataguard_smoke_test",
    description="Checks that the Airflow setup works end to end.",
    schedule=None,  # run manually only
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=10)},
    tags=["dataguard", "smoke-test"],
)
def dataguard_smoke_test():
    @task
    def say_hello() -> str:
        message = "Hello from DataGuard's Airflow!"
        print(message)
        return message

    @task
    def check_message(message: str) -> None:
        assert "DataGuard" in message, "Task output was not passed correctly"
        print(f"Received from previous task: {message}")

    check_message(say_hello())


dataguard_smoke_test()