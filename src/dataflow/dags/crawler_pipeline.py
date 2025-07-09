# src/dataflow/dags/crawler_pipeline.py
"""Airflow 工作流藍圖 (Airflow Workflow Blueprint)。

此 DAG 文件是爬蟲流程的最高級別調度器。它會動態地遍歷
`SourcePlatform` 枚舉中的所有成員，為每個平台自動創建一個
獨立的、結構相同的 Airflow DAG。

每個 DAG 都遵循標準的 `category_task >> urls_task >> details_task`
依賴關係，確保了數據處理流程的正確順序。
"""
from __future__ import annotations

import pendulum
from airflow.models.dag import DAG

from crawler.enums import SourcePlatform
from src.dataflow.etl.crawler import (
    create_category_task,
    create_urls_task,
    create_details_task,
)

# --- 動態生成 DAG ---
for platform in SourcePlatform:
    dag_id = f"crawler_pipeline_{platform.value}"

    with DAG(
        dag_id=dag_id,
        start_date=pendulum.datetime(2024, 1, 1, tz="Asia/Taipei"),
        schedule="0 3 * * *",  # 每天凌晨 3:00 執行
        catchup=False,
        tags=["crawler", platform.value],
        doc_md=f"為 {platform.value} 平台設計的端到端職缺爬取工作流。",
    ) as dag:
        
        # 步驟 1: 抓取分類 (如果平台需要)
        category_task = create_category_task(dag, platform)
        
        # 步驟 2: 抓取 URL 列表
        urls_task = create_urls_task(dag, platform)
        
        # 步驟 3: 抓取職缺詳情
        details_task = create_details_task(dag, platform, limit=5000)

        # 設置任務依賴關係
        if category_task:
            category_task >> urls_task >> details_task
        else:
            urls_task >> details_task