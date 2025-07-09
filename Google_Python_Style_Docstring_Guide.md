採用 Google Python Style Guide 的 Docstring 格式，並完全使用繁體中文。這種格式清晰、結構化，且被許多工具（如 Sphinx）良好支持。
規範細節如下:

1.檔案模組 (Module) Docstring:
每個檔案的開頭都應該有一個模組 Docstring。
第一行是模組的簡要說明。
接著是空一行，然後是更詳細的描述，說明該模組的職責、包含的主要組件等。

範例 (crawler/factory.py):
"""此模組提供一個工廠函數，用於動態創建和配置爬蟲實例。

這是策略模式的應用核心，它將客戶端代碼（如 Airflow 任務或 CLI 命令）
與具體的策略實現解耦。通過調用 `create_crawler`，客戶端可以獲取
一個針對特定平台、完全配置好的 `CrawlerOrchestrator`，而無需關心
其內部的組件是如何被實例化和組合的。
"""

2.類別 (Class) Docstring:
緊跟在 class 定義下方。
第一行是類別的簡要說明。
接著可以有詳細描述。
如果類別有重要的公開屬性，可以使用 Attributes: 區塊來說明。

範例 (crawler/core/orchestrator.py):
class CrawlerOrchestrator:
    """爬蟲流程編排器，是整個框架的核心大腦。

    它接收特定平台的策略組件（UrlFetcher, DetailFetcher, DetailParser），
    並負責執行標準化的兩階段爬取流程：`run_urls_pipeline` 和
    `run_details_pipeline`。此類別也處理了併發執行、錯誤捕獲、
    日誌記錄和數據持久化等通用邏輯。

    Attributes:
        platform (SourcePlatform): 當前編排器實例負責的平台。
        cfg (Any): 特定於該平台的配置。
        url_fetcher (UrlFetcher): 用於獲取職缺列表項的策略。
        detail_fetcher (DetailFetcher): 用於獲取職缺詳情內容的策略。
        detail_parser (DetailParser): 用於解析詳情並轉換為 Job 模型的策略。
        redis (RedisClient): 用於快取中介資料和失敗快照的 Redis 客戶端。
    """

3.函數/方法 (Function/Method) Docstring:
緊跟在 def 定義下方。
第一行是函數的簡要說明（祈使句，例如「執行...」而不是「這個函數執行...」）。
接著可以有詳細描述。
使用 Args: 區塊描述每個參數，格式為 參數名 (類型): 說明。。
使用 Returns: 區塊描述返回值，格式為 類型: 說明。。
如果函數可能拋出特定異常，使用 Raises: 區塊說明。

範例 (crawler/factory.py):
def create_crawler(platform: SourcePlatform, category_ids: Optional[List[str]] = None) -> CrawlerOrchestrator:
    """根據平台枚舉，實例化並返回一個配置好的 CrawlerOrchestrator。

    此工廠函數會根據傳入的平台，動態地從對應的 `strategies.py`
    模組中導入並實例化所需的策略組件。它還會從資料庫中獲取
    該平台對應的分類資訊，並將其傳遞給 `UrlFetcher`。

    Args:
        platform (SourcePlatform): 要為其創建爬蟲的來源平台。
        category_ids (Optional[List[str]]): 一個可選的分類 ID 列表。
            如果提供，只會抓取這些分類下的職缺。如果為 None，則
            抓取該平台所有可用分類。

    Returns:
        CrawlerOrchestrator: 一個為指定平台配置好的完整爬蟲編排器實例。
    
    Raises:
        ValueError: 如果傳入的平台未知或不受支持。
"""