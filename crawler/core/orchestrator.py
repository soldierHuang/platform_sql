# crawler/core/orchestrator.py
"""
此模組包含 CrawlerOrchestrator，是爬蟲框架的核心大腦。
"""
import logging
import json
from typing import Dict, Optional, Any
from urllib.parse import urlparse, urljoin

from crawler.enums import SourcePlatform, CrawlStatus
from crawler.database.schema import Url, Job
from crawler.database import repository
from crawler.cache import get_redis_client
from crawler.settings import settings
from crawler.utils import run_concurrently
from .protocols import UrlFetcher, DetailFetcher, DetailParser

logger = logging.getLogger(__name__)

class CrawlerOrchestrator:
    """
    爬蟲流程編排器。
    """
    def __init__(
        self,
        platform: SourcePlatform,
        url_fetcher: UrlFetcher,
        detail_fetcher: DetailFetcher,
        detail_parser: DetailParser,
    ):
        self.platform = platform
        self.cfg = self._get_platform_settings(platform)
        self.url_fetcher = url_fetcher
        self.detail_fetcher = detail_fetcher
        self.detail_parser = detail_parser
        self.redis = get_redis_client()
        logger.info(f"[{self.platform.value}] CrawlerOrchestrator initialized.")

    def _get_platform_settings(self, platform: SourcePlatform) -> Any:
        platform_setting_map = {
            SourcePlatform.PLATFORM_104: settings.p104,
            SourcePlatform.PLATFORM_1111: settings.p1111,
            SourcePlatform.PLATFORM_CAKERESUME: settings.pcake,
            SourcePlatform.PLATFORM_YES123: settings.pyes123,
        }
        if platform not in platform_setting_map:
            raise ValueError(f"Settings for platform '{platform.value}' not found.")
        return platform_setting_map[platform]


    def _extract_url_from_item(self, item: Dict[str, Any]) -> Optional[str]:
        """從 UrlFetcher 返回的原始 item 中提取 URL，並進行清理。"""
        url_path = None
        if isinstance(item, dict):
            url_path = item.get("url") or item.get("link", {}).get("job") or item.get("href")

        if not isinstance(url_path, str) or not url_path:
            logger.warning(f"[{self.platform.value}] Could not extract a valid URL path from item: {item}")
            return None

        if url_path.startswith("http"):
            return urlparse(url_path)._replace(query="").geturl()
        
        platform_base_url_map = {
            SourcePlatform.PLATFORM_CAKERESUME: "https://www.cakeresume.com",
            SourcePlatform.PLATFORM_YES123: "https://www.yes123.com.tw/wk_index/",
        }
        base_url = platform_base_url_map.get(self.platform)
        
        if base_url:
            full_url = urljoin(base_url, url_path)
            if self.platform == SourcePlatform.PLATFORM_YES123:
                return full_url
            return urlparse(full_url)._replace(query="").geturl()

        logger.warning(f"[{self.platform.value}] Could not determine base URL for relative path: {url_path}")
        return None

    def run_urls_pipeline(self):
        logger.info(f"[{self.platform.value}] Starting URL pipeline...")
        urls_to_sync = set()
        redis_pipe = self.redis.pipeline()
        items_processed = 0

        for item in self.url_fetcher():
            items_processed += 1
            url = self._extract_url_from_item(item)
            if not url:
                continue

            urls_to_sync.add(url)
            redis_key = f"meta:{self.platform.value}:{url}"
            redis_pipe.set(redis_key, json.dumps(item), ex=86400)

        logger.info(f"[{self.platform.value}] UrlFetcher yielded {items_processed} items.")

        if urls_to_sync:
            # [關鍵修正] 將 set 轉換為 list 再傳遞，避免類型錯誤
            repository.upsert_urls(self.platform, list(urls_to_sync))
            redis_pipe.execute()
            logger.info(f"[{self.platform.value}] Synced {len(urls_to_sync)} URLs to database and Redis.")
        else:
            logger.info(f"[{self.platform.value}] No new URLs found to sync.")

    def run_details_pipeline(self, limit: int):
        logger.info(f"[{self.platform.value}] Starting Details pipeline with limit {limit}...")
        urls_to_process = repository.get_unprocessed_urls(self.platform, limit)
        if not urls_to_process:
            logger.info(f"[{self.platform.value}] No unprocessed URLs found.")
            return

        jobs, url_status_map = [], {CrawlStatus.COMPLETED: [], CrawlStatus.FAILED: []}
        
        def process_single_url(url_obj: Url) -> tuple[Optional[Job], CrawlStatus]:
            redis_key = f"meta:{self.platform.value}:{url_obj.source_url}"
            intermediate_data_str = self.redis.get(redis_key)
            intermediate_data = json.loads(intermediate_data_str) if intermediate_data_str else {}

            try:
                raw_content = self.detail_fetcher(url_obj.source_url)
                if not raw_content:
                    raise ValueError("Fetched content is empty.")
                
                job = self.detail_parser(raw_content, url_obj.source_url, intermediate_data)
                if job:
                    return job, CrawlStatus.COMPLETED
                else:
                    raise ValueError("Parsing failed, parser returned None.")

            except Exception as e:
                logger.error(
                    f"[{self.platform.value}] Failed to process URL: {url_obj.source_url}. Reason: {e}",
                    exc_info=True
                )
                return None, CrawlStatus.FAILED

        results = list(run_concurrently(process_single_url, urls_to_process, self.cfg.max_workers))

        for i, result in enumerate(results):
            # Check if result is not None and is a tuple of size 2
            if result and isinstance(result, tuple) and len(result) == 2:
                job, status = result
                url = urls_to_process[i].source_url
                url_status_map[status].append(url)
                if job:
                    jobs.append(job)
            else:
                url = urls_to_process[i].source_url
                url_status_map[CrawlStatus.FAILED].append(url)
                logger.warning(f"Concurrent task for URL {url} returned an unexpected result: {result}")


        if jobs:
            logger.info(f"[{self.platform.value}] Preparing to upsert {len(jobs)} jobs. First job: source_job_id={jobs[0].source_job_id}, url={jobs[0].url}")
            repository.upsert_jobs(jobs)

        if url_status_map[CrawlStatus.COMPLETED] or url_status_map[CrawlStatus.FAILED]:
            logger.info(f"[{self.platform.value}] Marking URLs status: {len(url_status_map[CrawlStatus.COMPLETED])} COMPLETED, {len(url_status_map[CrawlStatus.FAILED])} FAILED.")
            repository.mark_urls_as_crawled(url_status_map)
        
        logger.info(f"[{self.platform.value}] Details pipeline finished.")