# crawler/factory.py
"""
此模組提供一個工廠函數 `create_crawler`，用於動態地創建和配置
特定平台的 CrawlerOrchestrator 實例。
"""
import logging
from typing import Any, Optional, List

from crawler.core.orchestrator import CrawlerOrchestrator
from crawler.core.protocols import CategoryFetcher
from crawler.enums import SourcePlatform
from crawler.database import repository
from crawler.settings import settings

logger = logging.getLogger(__name__)

def _get_platform_settings(platform: SourcePlatform) -> Any:
    """根據平台枚舉從全局配置中獲取對應的平台配置。"""
    platform_setting_map = {
        SourcePlatform.PLATFORM_104: settings.p104,
        SourcePlatform.PLATFORM_1111: settings.p1111,
        SourcePlatform.PLATFORM_CAKERESUME: settings.pcake,
        SourcePlatform.PLATFORM_YES123: settings.pyes123,
    }
    if platform not in platform_setting_map:
        raise ValueError(f"Settings for platform '{platform.value}' not found.")
    return platform_setting_map[platform]


def create_crawler(platform: SourcePlatform) -> CrawlerOrchestrator:
    """
    工廠函數：根據平台枚舉，實例化並返回一個配置好的 CrawlerOrchestrator。
    """
    logger.info(f"正在為平台 '{platform.value}' 創建爬蟲實例...")
    
    platform_settings = _get_platform_settings(platform)
    
    categories = repository.get_source_categories(platform)
    logger.info(f"從資料庫讀取到 {len(categories)} 個分類。")

    url_fetcher = None
    detail_fetcher = None
    detail_parser = None
    category_fetcher: Optional[CategoryFetcher] = None

    if platform == SourcePlatform.PLATFORM_104:
        from crawler.projects.platform_104 import strategies
        url_fetcher = strategies.ApiUrlFetcher(categories, platform_settings)
        detail_fetcher = strategies.ApiDetailFetcher(platform_settings)
        detail_parser = strategies.ApiDetailParser()
        category_fetcher = strategies.ApiCategoryFetcher(platform_settings)

    elif platform == SourcePlatform.PLATFORM_1111:
        from crawler.projects.platform_1111 import strategies
        url_fetcher = strategies.ApiUrlFetcher(categories, platform_settings)
        detail_fetcher = strategies.HtmlDetailFetcher(platform_settings)
        detail_parser = strategies.HybridDetailParser()
        category_fetcher = strategies.ApiCategoryFetcher(platform_settings)

    elif platform == SourcePlatform.PLATFORM_CAKERESUME:
        # [關鍵修正] Cakeresume 現在使用 HtmlUrlFetcher
        from crawler.projects.platform_cakeresume import strategies
        url_fetcher = strategies.HtmlUrlFetcher(categories, platform_settings)
        detail_fetcher = strategies.HtmlDetailFetcher(platform_settings)
        detail_parser = strategies.ScriptDetailParser()
        category_fetcher = strategies.HtmlCategoryFetcher(platform_settings)

    elif platform == SourcePlatform.PLATFORM_YES123:
        from crawler.projects.platform_yes123 import strategies
        url_fetcher = strategies.HtmlUrlFetcher(categories, platform_settings)
        detail_fetcher = strategies.HtmlDetailFetcher(platform_settings)
        detail_parser = strategies.HtmlDetailParser()
        category_fetcher = strategies.HtmlCategoryFetcher(platform_settings)
        
    else:
        raise ValueError(f"Crawler implementation for platform '{platform.value}' not found.")

    logger.info(f"[{platform.value}] 策略組件實例化完成。")
    return CrawlerOrchestrator(
        platform=platform,
        url_fetcher=url_fetcher,
        detail_fetcher=detail_fetcher,
        detail_parser=detail_parser,
        category_fetcher=category_fetcher,
    )