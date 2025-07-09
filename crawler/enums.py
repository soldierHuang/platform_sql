# crawler/enums.py
"""標準化字典 (Standardized Dictionary)。

此模組定義了整個應用程式中使用的標準化枚舉類型。
使用枚舉可以帶來以下好處：
1.  **防止拼寫錯誤**：在程式碼中使用 `CrawlStatus.PENDING` 而不是手動輸入 "pending" 字串。
2.  **代碼清晰度**：枚舉值自帶說明，使程式碼更易於閱讀和理解。
3.  **易於維護**：所有可能的狀態都集中在一個地方定義，方便未來修改或擴充。
"""
from enum import Enum

class SourcePlatform(str, Enum):
    """資料來源平台。用於在資料庫中標識數據的來源。"""
    PLATFORM_104 = "platform_104"
    PLATFORM_1111 = "platform_1111"
    PLATFORM_CAKERESUME = "platform_cakeresume"
    PLATFORM_YES123 = "platform_yes123"

class JobStatus(str, Enum):
    """職缺或 URL 的活躍狀態。"""
    ACTIVE = "active"
    INACTIVE = "inactive"

class CrawlStatus(str, Enum):
    """職缺詳情頁的抓取狀態。"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class SalaryType(str, Enum):
    """標準化的薪資給付週期。"""
    MONTHLY = "MONTHLY"
    HOURLY = "HOURLY"
    YEARLY = "YEARLY"
    DAILY = "DAILY"
    BY_CASE = "BY_CASE"
    NEGOTIABLE = "NEGOTIABLE"

class JobType(str, Enum):
    """標準化的工作類型。"""
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    TEMPORARY = "TEMPORARY"