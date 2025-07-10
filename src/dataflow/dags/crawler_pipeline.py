# src/dataflow/dags/crawler_pipeline.py
"""Airflow 工作流藍圖 (Airflow Workflow Blueprint)"""
from __future__ import annotations

import pendulum
from airflow.models.dag import DAG

from src.dataflow.etl.crawler import (
    SourcePlatform,
    create_category_task,
    create_details_task,
    create_urls_task,
)

# --- 動態生成 DAG ---
for platform in SourcePlatform:
    dag_id = f"crawler_pipeline_{platform.value}"
    with DAG(
        dag_id=dag_id,
        start_date=pendulum.datetime(2024, 1, 1, tz="Asia/Taipei"),
        schedule="0 3 * * *",
        catchup=False,
        tags=["crawler", platform.value],
        doc_md=f"為 {platform.value} 平台設計的端到端職缺爬取工作流。",
    ) as dag:
        category_task = create_category_task(dag=dag, platform=platform)
        urls_task = create_urls_task(dag=dag, platform=platform)
        details_task = create_details_task(dag=dag, platform=platform, limit=5000)

        if category_task:
            category_task >> urls_task >> details_task
        else:
            urls_task >> details_task