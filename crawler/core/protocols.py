# crawler/core/protocols.py
"""接口藍圖 (Contracts)。

此模組使用 typing.Protocol 定義了爬蟲框架的核心策略接口。
這些接口定義了爬蟲框架中各個可插拔組件必須遵守的「契約」，
確保了框架的靈活性和可擴展性。它們讓 `Orchestrator` 可以
與任何遵守這些契約的平台實現進行交互，而無需關心其內部細節。
"""
from typing import Protocol, Optional, Dict, Any, Generator
from crawler.database.schema import Job

class UrlFetcher(Protocol):
    """
    策略接口：定義如何獲取一個平台所有職缺的原始資料項。

    實現此協議的類必須提供一個 __call__ 方法，該方法作為一個生成器，
    逐批 yield 從 API 或 HTML 解析出的原始資料項（例如，API 返回的 job dict）。
    這些資料項將被傳遞給後續流程作為中介資料，存儲在 Redis 中。
    """
    def __call__(self) -> Generator[Dict[str, Any], None, None]:
        ...

class DetailFetcher(Protocol):
    """
    策略接口：定義如何根據 URL 獲取單一職缺的詳細內容。

    實現此協議的類必須提供一個 __call__ 方法，該方法接收一個 URL 字串，
    並返回該 URL 對應的詳細頁面的原始內容（通常是 HTML 或 JSON 格式的字串）。
    如果獲取失敗，應返回空字串或在 `make_request` 中拋出異常。
    """
    def __call__(self, url: str) -> str:
        ...

class DetailParser(Protocol):
    """
    策略接口：定義如何將原始詳細內容解析為標準化的 Job 模型。

    實現此協議的類必須提供一個 __call__ 方法，該方法接收從 DetailFetcher
    獲取的原始內容、職缺 URL 以及從 UrlFetcher 傳遞過來的中介資料。
    其核心職責是將這些異構的輸入數據，轉換為一個標準化的、可選的 Job 物件。
    如果解析失敗或數據無效，應返回 None 或拋出具體的異常。
    """
    def __call__(self, raw_content: str, url: str, intermediate_data: Optional[Dict[str, Any]]) -> Optional[Job]:
        ...