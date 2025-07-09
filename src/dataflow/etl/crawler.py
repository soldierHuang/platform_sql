# src/dataflow/etl/crawler.py
"""Airflow Task 工廠 (Airflow Task Factory)。

此模組提供了一系列輔助函數，用於創建 Airflow 的 Task Operator。
它封裝了調用 Celery 任務的複雜性，使得在 DAG 文件中定義任務變得
非常簡潔和標準化。
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, List, Optional

from airflow.operators.python import PythonOperator
from airflow.providers.celery.operators.celery import CeleryOperator

from crawler.enums import SourcePlatform

if TYPE_CHECKING:
    from airflow.models.dag import DAG

logger = logging.getLogger(__name__)

def _trigger_celery_task(task_name: str, task_kwargs: dict):
    """一個輔助函數，用於在 Airflow 中觸發 Celery 任務。"""
    from crawler.app import app
    logger.info(f"正在從 Airflow 觸發 Celery 任務 '{task_name}'，參數: {task_kwargs}")
    app.send_task(task_name, kwargs=task_kwargs)
    logger.info(f"任務 '{task_name}' 已成功發送到 Celery 隊列。")

def create_category_task(dag: DAG, platform: SourcePlatform) -> Optional[PythonOperator]:
    """為需要抓取分類的平台創建一個 Airflow task。"""
    # [修改] 將所有平台都納入分類任務檢查
    task_name_map = {
        SourcePlatform.PLATFORM_104: "platform_104.run_category_pipeline",
        SourcePlatform.PLATFORM_1111: "platform_1111.run_category_pipeline",
        SourcePlatform.PLATFORM_CAKERESUME: "platform_cakeresume.run_category_pipeline",
        SourcePlatform.PLATFORM_YES123: "platform_yes123.run_category_pipeline",
    }
    
    if platform not in task_name_map:
        return None
    
    task_id = f"{platform.value}_category"
    task_name = task_name_map[platform]

    return PythonOperator(
        task_id=task_id,
        python_callable=_trigger_celery_task,
        op_kwargs={"task_name": task_name, "task_kwargs": {}},
        dag=dag,
    )

def create_urls_task(
    dag: DAG, 
    platform: SourcePlatform, 
    category_ids: Optional[List[str]] = None
) -> PythonOperator:
    """創建一個觸發 URL 抓取流程的 Airflow task。"""
    task_id = f"{platform.value}_urls"
    task_kwargs = {"platform_name": platform.value}
    if category_ids:
        task_kwargs["category_ids"] = category_ids

    return PythonOperator(
        task_id=task_id,
        python_callable=_trigger_celery_task,
        op_kwargs={
            "task_name": "crawler.run_urls_pipeline",
            "task_kwargs": task_kwargs
        },
        dag=dag,
    )

def create_details_task(dag: DAG, platform: SourcePlatform, limit: int = 2000) -> PythonOperator:
    """創建一個觸發職缺詳情抓取流程的 Airflow task。"""
    task_id = f"{platform.value}_details"
    return PythonOperator(
        task_id=task_id,
        python_callable=_trigger_celery_task,
        op_kwargs={
            "task_name": "crawler.run_details_pipeline",
            "task_kwargs": {"platform_name": platform.value, "limit": limit}
        },
        dag=dag,
    )