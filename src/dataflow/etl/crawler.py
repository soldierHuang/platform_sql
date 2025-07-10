# src/dataflow/etl/crawler.py
"""Airflow Task 工廠 (Airflow Task Factory) - 使用 CeleryOperator。"""
from __future__ import annotations
import logging
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from airflow.operators.python import PythonOperator


def _run_celery_task(task_name: str, **kwargs):
    """Helper function to run Celery tasks."""
    from celery import Celery
    from crawler.app import celery_app

    celery_app.send_task(task_name, kwargs=kwargs)


def create_category_task(dag: DAG, platform: SourcePlatform) -> Optional[BaseOperator]:
    """為需要抓取分類的平台創建一個觸發 Celery 任務的 Airflow task。"""
    task_name_map = {
        SourcePlatform.PLATFORM_104: "platform_104.run_category_pipeline",
        SourcePlatform.PLATFORM_1111: "platform_1111.run_category_pipeline",
        SourcePlatform.PLATFORM_CAKERESUME: "platform_cakeresume.run_category_pipeline",
        SourcePlatform.PLATFORM_YES123: "platform_yes123.run_category_pipeline",
    }
    
    if platform not in task_name_map:
        return None
    
    return PythonOperator(
        task_id=f"{platform.value}_category",
        python_callable=_run_celery_task,
        op_kwargs={
            "task_name": task_name_map[platform],
        },
        dag=dag,
    )

def create_urls_task(
    dag: DAG, 
    platform: SourcePlatform, 
    category_ids: Optional[List[str]] = None
) -> BaseOperator:
    """創建一個觸發 URL 抓取流程的 Airflow task。"""
    task_kwargs = {"platform_name": platform.value}
    
    return PythonOperator(
        task_id=f"{platform.value}_urls",
        python_callable=_run_celery_task,
        op_kwargs={
            "task_name": "crawler.run_urls_pipeline",
            "kwargs": task_kwargs,
        },
        dag=dag,
    )

def create_details_task(dag: DAG, platform: SourcePlatform, limit: int = 5000) -> BaseOperator:
    """創建一個觸發職缺詳情抓取流程的 Airflow task。"""
    task_kwargs = {"platform_name": platform.value, "limit": limit}

    return PythonOperator(
        task_id=f"{platform.value}_details",
        python_callable=_run_celery_task,
        op_kwargs={
            "task_name": "crawler.run_details_pipeline",
            "kwargs": task_kwargs,
        },
        dag=dag,
    )