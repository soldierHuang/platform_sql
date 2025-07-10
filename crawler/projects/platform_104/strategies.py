# crawler/projects/platform_104/strategies.py
"""104平台的特種兵 (API Specialist)。

此模組為 104 平台實現了 `UrlFetcher`, `DetailFetcher`, `DetailParser` 策略接口。
所有策略都基於 104 的公開 API 進行數據交互，實現了高效且穩定的數據獲取。
"""
import logging
import json
from typing import List, Dict, Any, Generator, Optional

from crawler.core.protocols import UrlFetcher, DetailFetcher, DetailParser
from crawler.utils import make_request
from crawler.database.schema import Job, CategorySource
from . import parsers

logger = logging.getLogger(__name__)

class ApiCategoryFetcher:
    """策略實現：從 104 API 獲取職務分類數據。"""
    def __init__(self, settings: Any):
        self.cfg = settings

    def __call__(self) -> List[Dict[str, Any]]:
        logger.info("[104] 開始從 API 獲取職務分類。")
        api_url = "https://static.104.com.tw/category-tool/json/JobCat.json"
        res = make_request(api_url, headers=self.cfg.headers)
        json_data = res.json()
        transformed_data = parsers.transform_categories_to_source_model(json_data)
        logger.info(f"[104] 成功獲取並轉換 {len(transformed_data)} 個職務分類。")
        return transformed_data

class ApiUrlFetcher:
    """策略實現：通過 104 的搜索 API 獲取職缺列表。"""
    def __init__(self, categories: List[CategorySource], settings: Any):
        self.categories = categories
        self.cfg = settings

    def __call__(self) -> Generator[Dict[str, Any], None, None]:
        if not self.categories:
            logger.warning("[104] UrlFetcher 未收到任何分類，將跳過 URL 抓取。")
            return

        logger.info(f"[104] 開始為 {len(self.categories)} 個分類抓取 URL。")
        for cat in self.categories:
            logger.debug(f"[104] 正在抓取分類: {cat.source_category_name} ({cat.source_category_id})")
            for page in range(1, self.cfg.max_pages + 1):
                params = {
                    "ro": 0,
                    "jobCat": cat.source_category_id,
                    "order": 16,
                    "page": page,
                    "isnew": 30,
                }
                try:
                    res = make_request(
                        "https://www.104.com.tw/jobs/search/list",
                        headers=self.cfg.headers,
                        params=params
                    )
                    data = res.json().get("data", {})
                    jobs = data.get("list", [])

                    if not jobs:
                        logger.info(f"[104] 分類 {cat.source_category_id} 在第 {page} 頁已無更多職缺。")
                        break

                    logger.debug(f"[104] 於分類 {cat.source_category_id} 第 {page} 頁獲取 {len(jobs)} 個職缺。")
                    for job_item in jobs:
                        # 並將相對 URL 轉換為絕對 URL
                        if 'job' in job_item.get('link', {}):
                            job_item["link"]["job"] = f"https:{job_item['link']['job']}"
                        yield job_item

                except Exception as e:
                    logger.error(f"[104] 抓取 URL 列表失敗 (分類: {cat.source_category_id}, 頁數: {page}): {e}", exc_info=True)
                    break

class ApiDetailFetcher:
    """策略實現：通過 104 的內容 API 獲取職缺詳情 JSON。"""
    def __init__(self, settings: Any):
        self.cfg = settings

    def __call__(self, url: str) -> str:
        job_id = url.split("/")[-1].split("?")[0]
        api_url = f"https://www.104.com.tw/job/ajax/content/{job_id}"
        
        headers = {**self.cfg.headers, "Referer": url}
        res = make_request(api_url, headers=headers)
        return res.text # 直接返回 JSON 字符串

class ApiDetailParser:
    """策略實現：將從 API 獲取的 JSON 數據解析為 Job 模型。"""
    def __call__(self, raw_content: str, url: str, intermediate_data: Optional[Dict[str, Any]]) -> Optional[Job]:
        try:
            api_response = json.loads(raw_content)
            job_api_data = api_response.get("data")
            if not job_api_data:
                raise ValueError("詳情 API 響應中缺少 'data' 鍵。")
            return parsers.transform_details_to_job_model(job_api_data, url)
        except json.JSONDecodeError:
            logger.error(f"[104] 無法解析來自 {url} 的 JSON 內容。")
            raise # 向上拋出，讓 Orchestrator 捕獲
        except ValueError as e:
            logger.error(f"[104] 解析來自 {url} 的數據失敗: {e}")
            raise