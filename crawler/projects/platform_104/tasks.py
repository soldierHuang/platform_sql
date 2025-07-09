# crawler/projects/platform_104/tasks.py
"""104平台的分類抓取器 (Category Fetcher)。

定義一個專屬的 Celery 任務 `run_category_pipeline`，此任務負責從
104 的 `JobCat.json` API 獲取所有職務分類，並調用 `repository`
將其同步到資料庫中。根據全局配置，此任務會被自動路由到專用的
`category_queue` 隊列中執行。
"""
import logging

from crawler.app import app
from crawler.enums import SourcePlatform
from crawler.database import repository
from crawler.utils import make_request
from crawler.settings import settings
from . import parsers

logger = logging.getLogger(__name__)

@app.task(bind=True, name="platform_104.run_category_pipeline", acks_late=True, time_limit=600)
def run_category_pipeline(self) -> None:
    """從 104 API 獲取職務分類並同步到資料庫。"""
    try:
        logger.info("[104] 開始執行分類抓取 pipeline...")
        cfg = settings.p104
        api_url = "https://static.104.com.tw/category-tool/json/JobCat.json"
        
        res = make_request(api_url, headers=cfg.headers)
        json_data = res.json()
        
        transformed_data = parsers.transform_categories_to_source_model(json_data)
        result = repository.sync_source_categories(SourcePlatform.PLATFORM_104, transformed_data)
        
        logger.info(f"[104] 分類 pipeline 成功完成。同步結果: {result}")
        
    except Exception as e:
        logger.error(f"[104] 分類 pipeline 失敗: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=180)