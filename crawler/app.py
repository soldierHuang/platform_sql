# crawler/app.py
"""Celery 的大腦 (Celery's Brain)。

此模組負責定義和配置 Celery 應用實例。它會自動發現項目中所有
名為 'tasks.py' 的模組並加載其中的任務。

最關鍵的配置是 `task_routes`，它實現了我們設計的「雙隊列」模式，
將耗時較短但重要的分類任務（`run_category_pipeline`）路由到
專用的 `category_queue`，而將所有常規的爬取任務保留在 `default`
隊列，從而實現了任務隔離和資源的有效利用。
"""
from pathlib import Path
from celery import Celery
from crawler.settings import celery_broker_url, celery_result_backend

def find_task_modules() -> list[str]:
    """自動發現 'crawler' 目錄及其子目錄下所有名為 'tasks.py' 的模組。"""
    crawler_root = Path(__file__).parent
    modules = []
    # 遍歷所有 tasks.py 文件
    for path in crawler_root.rglob('tasks.py'):
        # 轉換成模組導入路徑，例如 crawler/projects/platform_104/tasks.py -> crawler.projects.platform_104.tasks
        relative_path = path.relative_to(crawler_root.parent)
        module_path = str(relative_path).replace('/', '.').replace('\\', '.').removesuffix('.py')
        modules.append(module_path)
    
    # 確保 crawler/tasks.py (如果存在) 也被包含
    if (crawler_root / "tasks.py").exists() and "crawler.tasks" not in modules:
        modules.append("crawler.tasks")
        
    return modules

# 動態查找所有任務模組
task_modules_to_include = find_task_modules()

app = Celery(
    "crawler_app",
    broker=celery_broker_url,
    backend=celery_result_backend,
    include=task_modules_to_include
)

# --- 全局 Celery 配置 ---
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Taipei",
    enable_utc=True, # 建議使用 UTC 時間以避免時區問題
    result_expires=3600, # 任務結果在 1 小時後過期
    task_acks_late=True, # 任務執行完畢後才發送確認，防止 worker 崩潰導致任務丟失
    worker_prefetch_multiplier=1, # 每個 worker 一次只取一個任務，避免任務飢餓
    # [核心] 任務路由配置，實現雙隊列調度
    # 將所有以 'run_category_pipeline' 結尾的任務路由到 'category_queue'
    task_routes={
        '*.run_category_pipeline': {'queue': 'category_queue'},
    },
    
    # 設置默認隊列，所有未被路由的任務都會進入此隊列
    task_default_queue="default",
)