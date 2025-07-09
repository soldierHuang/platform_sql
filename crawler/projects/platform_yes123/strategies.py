# crawler/projects/platform_yes123/strategies.py
import logging
from typing import Dict, Any, Generator, Optional, List

from bs4 import BeautifulSoup

from crawler.core.protocols import UrlFetcher, DetailFetcher, DetailParser
from crawler.utils import make_request
from crawler.database.schema import Job, CategorySource
from . import parsers

logger = logging.getLogger(__name__)

class HtmlUrlFetcher:
    def __init__(self, categories: List[CategorySource], settings: Any):
        self.categories = categories
        self.cfg = settings

    def _fetch_urls_by_params(self, params: Dict[str, Any], url_path: str) -> Generator[Dict[str, Any], None, None]:
        base_url = "https://www.yes123.com.tw/wk_index/"
        target_url = f"{base_url}{url_path}"

        for page in range(1, self.cfg.max_pages + 1):
            if page > 1:
                params["strrec"] = (page - 1) * 20
            
            try:
                res = make_request(target_url, headers=self.cfg.headers, params=params, verify=False)
                res.encoding = 'big5'
                soup = BeautifulSoup(res.text, "html.parser")
                
                selector = 'a[href^="job.asp?p_id="]'
                job_links = soup.select(selector)
                
                if not job_links:
                    logger.info(f"[yes123] 在 URL {target_url} 參數 {params} 的第 {page} 頁未找到任何職缺連結。")
                    break
                
                for a_tag in job_links:
                    if href := a_tag.get('href'):
                        yield {"href": href}

            except Exception as e:
                logger.error(f"[yes123] 抓取 URL 列表頁面失敗 (URL: {target_url}, 參數: {params}, 頁數: {page}): {e}", exc_info=True)
                break

    def __call__(self) -> Generator[Dict[str, Any], None, None]:
        if self.categories:
            logger.info(f"[yes123] 開始為 {len(self.categories)} 個分類抓取 URL。")
            for cat in self.categories:
                if '_' not in cat.source_category_id:
                    continue
                logger.debug(f"[yes123] 正在抓取分類: {cat.source_category_name} ({cat.source_category_id})")
                params = {
                    "find_work_mode1": cat.source_category_id,
                    "order_by": "m_date",
                    "order_ascend": "desc",
                }
                yield from self._fetch_urls_by_params(params, url_path="joblist.asp")
        else:
            logger.warning("[yes123] 未提供任何分類，將回退到通用總覽頁抓取模式。")
            yield from self._fetch_urls_by_params({}, url_path="job.asp")

class HtmlDetailFetcher:
    def __init__(self, settings: Any):
        self.cfg = settings

    def __call__(self, url: str) -> str:
        res = make_request(url, headers=self.cfg.headers, verify=False)
        return res.text

class HtmlDetailParser:
    def __call__(self, raw_content: str, url: str, intermediate_data: Optional[Dict[str, Any]]) -> Optional[Job]:
        return parsers.transform_details_to_job_model(raw_content, url)