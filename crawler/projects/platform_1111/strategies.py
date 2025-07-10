# crawler/projects/platform_1111/strategies.py
"""1111平台的混合戰術專家 (Hybrid Specialist)。

此模組為 1111 平台實現了三大策略接口。它採用了「API列表 + HTML詳情」
的混合模式，以應對 1111 網站前端渲染和後端 API 並存的情況。
"""
import logging
from typing import List, Dict, Any, Generator, Optional
import urllib.parse

from crawler.core.protocols import UrlFetcher, DetailFetcher, DetailParser
from crawler.utils import make_request
from crawler.database.schema import Job, CategorySource
from . import parsers

logger = logging.getLogger(__name__)

class ApiCategoryFetcher:
    """策略實現：從 1111 API 獲取職務分類數據。"""
    def __init__(self, settings: Any):
        self.cfg = settings

    def __call__(self) -> List[Dict[str, Any]]:
        logger.info("[1111] 開始從 API 獲取職務分類。")
        api_url = "https://www.1111.com.tw/api/v1/codeCategories/"
        res = make_request(api_url, headers=self.cfg.headers, verify=False)
        json_data = res.json()
        transformed_data = parsers.transform_categories_to_source_model(json_data)
        logger.info(f"[1111] 成功獲取並轉換 {len(transformed_data)} 個職務分類。")
        return transformed_data

class ApiUrlFetcher:
    """
    策略實現：通過 1111 的搜索 API 獲取職缺列表。

    此提取器使用 1111 人力銀行的內部 API 來獲取職缺列表。
    它會迭代預設的最大頁數，並為每個分類獲取數據。

    Attributes:
        categories (List[CategorySource]): 從資料庫獲取的分類列表。
        cfg (Any): 1111 平台的配置。
    """
    def __init__(self, categories: List[CategorySource], settings: Any):
        self.categories = categories
        self.cfg = settings

    def __call__(self) -> Generator[Dict[str, Any], None, None]:
        if not self.categories:
            logger.warning("[1111] UrlFetcher 未收到任何分類，將跳過 URL 抓取。")
            return

        logger.info(f"[1111] 開始為 {len(self.categories)} 個分類抓取 URL。")
        for cat in self.categories:
            logger.debug(f"[1111] 正在抓取分類: {cat.source_category_name} ({cat.source_category_id})")
            for page in range(1, self.cfg.max_pages + 1):
                # 構建符合 API 要求的 searchUrl 參數
                # 注意：1111 的這個 API 需要一個 'searchUrl' 參數來模擬前端的請求路徑
                # 這裡使用 urllib.parse.quote 對 category_id 進行編碼，確保 URL 安全
                encoded_job_position = urllib.parse.quote(cat.source_category_id)
                search_url_param = f"/search/job?page={page}&col=da&sort=desc&d0={encoded_job_position}"
                
                params = {
                    "page": page,
                    "sortBy": "da", # 依更新日期排序 ('da' for date, 'ab' for relevance)
                    "sortOrder": "desc", # 降序 (desc)
                    "jobPositions": cat.source_category_id, # 職務分類 ID
                    "conditionsText": "", # 關鍵字 (設置為空字串以匹配所有)
                    "searchUrl": search_url_param, # 模擬前端的 URL
                }

                try:
                    res = make_request(
                        "https://www.1111.com.tw/api/v1/search/jobs/",
                        headers=self.cfg.headers,
                        params=params,
                        verify=False # 1111 的 API 需要關閉 SSL 驗證
                    )
                    data = res.json().get("result", {})
                    jobs = data.get("hits", [])

                    if not jobs:
                        logger.info(f"[1111] 分類 {cat.source_category_id} 在第 {page} 頁已無更多職缺。")
                        break

                    logger.debug(f"[1111] 於分類 {cat.source_category_id} 第 {page} 頁獲取 {len(jobs)} 個職缺。")
                    for job_item in jobs:
                        if job_id := job_item.get("jobId"):
                            # 將 job_item 作為原始資料項 (intermediate data) 傳遞
                            # Orchestrator 會使用它來儲存到 Redis，並在詳情頁抓取時回傳
                            job_item['url'] = f"https://www.1111.com.tw/job/{job_id}" # 添加完整 URL 供 Orchestrator 提取
                            yield job_item
                        else:
                            logger.warning(f"[1111] 職缺項目缺少 'jobId': {job_item}")

                except Exception as e:
                    logger.error(f"[1111] 抓取 URL 列表失敗 (分類: {cat.source_category_id}, 頁數: {page}): {e}", exc_info=True)
                    break

class HtmlDetailFetcher:
    """
    策略實現：抓取 1111 職缺詳情頁的 HTML。

    Attributes:
        cfg (Any): 1111 平台的配置。
    """
    def __init__(self, settings: Any):
        self.cfg = settings

    def __call__(self, url: str) -> str:
        """
        發起 HTTP 請求獲取職缺詳情頁的完整 HTML 內容。

        Args:
            url (str): 職缺詳情頁的 URL。

        Returns:
            str: 頁面的原始 HTML 內容。
        """
        # 1111 的網站可能使用自簽名證書或有其他 SSL 問題，因此關閉驗證
        try:
            res = make_request(url, headers=self.cfg.headers, verify=False)
            return res.text
        except Exception as e:
            logger.error(f"[1111] 獲取職缺詳情 HTML 失敗 for URL {url}: {e}", exc_info=True)
            return "" # 返回空字符串，讓解析器處理空內容或導致解析器拋出錯誤

class HybridDetailParser:
    """
    策略實現：結合 HTML 內容和來自 Redis 的中介 API 數據進行解析。
    此解析器將 HTML 內容和從 `ApiUrlFetcher` 階段保存的中介數據（通常包含公司名和 Job ID）
    一同傳遞給 `parsers.transform_details_to_job_model` 進行解析。
    """
    def __call__(self, raw_content: str, url: str, intermediate_data: Optional[Dict[str, Any]]) -> Optional[Job]:
        """
        解析職缺詳情，優先使用中介數據（來自列表 API）補充 HTML 解析的不足。

        Args:
            raw_content (str): 職缺詳情頁的原始 HTML 內容。
            url (str): 職缺的 URL。
            intermediate_data (Optional[Dict[str, Any]]): 從 Redis 獲取的中介數據，包含原始列表項信息。

        Returns:
            Optional[Job]: 解析後的 Job 模型物件，如果解析失敗則返回 None。

        Raises:
            ValueError: 如果缺少必要的中介數據。
        """
        if not intermediate_data:
            raise ValueError("缺少來自列表 API 的中介數據 (intermediate_data)，無法進行解析。")
        
        # 將 HTML 內容和中介數據一起傳遞給 parser
        return parsers.transform_details_to_job_model(intermediate_data, raw_content, url)