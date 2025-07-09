# crawler/worker.py
"""Celery 工人監控器 (Worker Monitor)。

這個簡單的腳本利用 Celery 的信號機制 (`on_after_configure`)，
在 worker 啟動並配置完成後，打印出所有已成功註冊的任務列表。
這在開發和調試階段非常有用，可以快速確認我們的任務是否被 Celery 正確識別。
"""
import logging
from .app import app

logger = logging.getLogger(__name__)

# 使用 Celery 信號，在 worker 配置完成後執行此函數
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """在 Celery worker 啟動後，打印已註冊的任務信息。"""
    logger.info("Celery Worker 已配置完成。已註冊的任務列表:")
    # 過濾掉 Celery 內部的任務，只顯示我們自定義的任務
    user_tasks = [task for task in sorted(sender.tasks.keys()) if not task.startswith("celery.")]
    if user_tasks:
        for task_name in user_tasks:
            logger.info(f"  - {task_name}")
    else:
        logger.warning("未發現任何自定義的 Celery 任務。請檢查 'tasks.py' 文件和 `app.conf.include` 配置。")