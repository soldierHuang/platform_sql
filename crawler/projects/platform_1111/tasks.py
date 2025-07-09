# crawler/projects/platform_1111/tasks.py
"""1111平台的分類抓取器 (Category Fetcher)。

定義一個專屬的 Celery 任務 `run_category_pipeline`，負責從
1111 的 `codeCategories` API 獲取所有職務分類，並同步到資料庫。
"""
import logging

from crawler.app import app
from crawler.enums import SourcePlatform
from crawler.database import repository
from crawler.utils import make_request
from crawler.settings import settings
from . import parsers

logger = logging.getLogger(__name__)

@app.task(bind=True, name="platform_1111.run_category_pipeline", acks_late=True, time_limit=600)
def run_category_pipeline(self) -> None:
    """從 1111 API 獲取職務分類並同步到資料庫。"""
    try:
        logger.info("[1111] run_category_pipeline 函數開始執行。")
        logger.info("[1111] 開始執行分類抓取 pipeline...")
        cfg = settings.p1111
        api_url = "https://www.1111.com.tw/api/v1/codeCategories/"
        
        # 1111 的 API 需要關閉 SSL 驗證
        res = make_request(api_url, headers=cfg.headers, verify=False)
        logger.info(f"[1111] API 原始回應文本: {res.text}")
        api_response_data = res.json()
        logger.info(f"[1111] API 回應數據: {api_response_data}")
        
        transformed_data = parsers.transform_categories_to_source_model(api_response_data)
        if not transformed_data:
            logger.warning("[1111] 分類數據轉換後為空，請檢查 parser 邏輯和 API 響應。")
            return

        result = repository.sync_source_categories(SourcePlatform.PLATFORM_1111, transformed_data)
        logger.info(f"[1111] 分類 pipeline 成功完成。同步結果: {result}")

    except Exception as e:
        logger.error(f"[1111] 分類 pipeline 失敗: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=180)