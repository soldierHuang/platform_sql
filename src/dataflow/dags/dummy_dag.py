from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="dummy_dag",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=["dummy"],
) as dag:
    start_task = BashOperator(
        task_id="start",
        bash_command="echo 'Dummy DAG started!'",
    )

    end_task = BashOperator(
        task_id="end",
        bash_command="echo 'Dummy DAG finished!'",
    )

    start_task >> end_task
