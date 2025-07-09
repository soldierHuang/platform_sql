# 專案架構與設計理念

> 本文件是專案的「設計藍圖」，旨在深入闡述架構的設計思想與各模組的職責。
> 它與 `README.md` 的「快速入門」和 `v1/v2` 的「操作手冊」形成互補，幫助開發者理解系統的「為何如此設計」。

---

## 核心設計思想

這個架構採用 **策略模式 (Strategy Pattern)** 和 **關注點分離 (Separation of Concerns)** 的設計思想，將一個複雜的系統拆解成了多個高內聚、低耦合的模組：

- **`crawler/core/`**: **框架的大腦 (The Brain)**。定義了爬蟲「怎麼做」(How)，即標準化的爬取流程和策略接口，與具體平台無關。
- **`crawler/projects/`**: **平台的四肢 (The Limbs)**。定義了爬蟲「做什麼」(What)，即每個平台如何獲取 URL、抓取詳情和解析數據的具體實現。
- **`crawler/factory.py`**: **組裝工廠 (The Factory)**。將「大腦」和「四肢」靈活地組合在一起，根據指令創建出針對特定平台的完整爬蟲。
- **`crawler/database/`**: **記憶系統 (The Memory)**。負責與 SQL 資料庫的所有交互，是數據的唯一持久化層。
- **`crawler/cli.py` & `src/dataflow/`**: **神經系統/觸發器 (The Triggers)**。是整個爬蟲應用的入口，負責從外部（手動命令或 Airflow 調度）發起任務。
- **`settings.py`, `enums.py`, `utils.py`, `cache.py`**: **支撐系統 (The Support System)**。提供配置、常量、工具函數和快取等全項目共享的通用能力。

---

## 文件結構概覽

```
.
├── docker-compose.yml        # [本地開發] 定義 app, worker-default, worker-category, flower 等服務，實現雙隊列任務調度。
├── docker_stack.yml          # [生產環境] 用於 Docker Swarm 部署的 stack 設定檔，包含 restart_policy 等高可用性配置。
├── Dockerfile                # 採用多階段構建，使用 uv 加速依賴安裝，創建更小、更安全的生產鏡像。
├── requirements.txt          # 項目依賴包列表。
├── QA.md                     # 記錄項目重構過程中的問題與決策日誌。
├── src/
│   └── dataflow/
│       ├── dags/
│       │   └── crawler_pipeline.py # Airflow DAG 文件，動態為所有平台生成 category >> urls >> details 的工作流。
│       └── etl/
│           └── crawler.py        # Airflow Task 工廠，提供創建 Celery Operator 的輔助函數。
└── crawler/
    ├── __init__.py             # Python 包初始化文件。
    ├── app.py                  # Celery 應用定義。自動發現任務模組，配置雙隊列路由。
    ├── cache.py                # Redis 客戶端管理器，提供單例的 Redis 連接。
    ├── cli.py                  # 基於 Typer 的命令行工具，增加手動觸發 pipeline、指定分類、以及 debug-url 等強大維運功能。
    ├── enums.py                # 定義 SourcePlatform, CrawlStatus 等標準化枚舉。
    ├── factory.py              # 實作 create_crawler 工廠函數，根據平台動態組裝策略組件，並支持指定分類。
    ├── settings.py             # 基於 Pydantic 的唯一配置中心，管理所有平台和基礎設施配置。
    ├── utils.py                # 通用工具函數庫，如帶重試的 make_request、文本清理和安全提取。
    ├── worker.py               # Celery worker 啟動輔助腳本。
    ├── api/
    │   ├── __init__.py           # Python 包初始化文件。
    │   ├── dependencies.py       # FastAPI 依賴注入，提供 DB Session。
    │   └── main.py               # API 入口，提供查詢已爬取數據的端點。
    ├── core/
    │   ├── __init__.py           # Python 包初始化文件。
    │   ├── orchestrator.py       # CrawlerOrchestrator，實現標準化爬取流程、併發處理、錯誤快照記錄和 URL 提取優化。
    │   └── protocols.py          # 使用 typing.Protocol 定義三大策略接口，是框架的契約。
    ├── database/
    │   ├── __init__.py           # Python 包初始化文件。
    │   ├── connection.py         # 資料庫連接管理器，帶有強大的 Tenacity 重試機制。
    │   ├── repository.py         # 封裝所有 SQL 操作，實現數據訪問隔離層。
    │   └── schema.py             # 使用 SQLModel 定義 CategorySource, Url, Job 三大核心表結構。
    └── projects/
        ├── platform_104/
        │   ├── parsers.py          # 104 平台數據轉換純函數。
        │   ├── strategies.py       # 104 平台三大策略接口的 API 實現。
        │   └── tasks.py            # 104 平台專屬的分類抓取 Celery 任務。
        ├── platform_1111/
        │   ├── parsers.py          # 1111 平台數據轉換純函數。
        │   ├── strategies.py       # 1111 平台三大策略接口的混合實現。
        │   └── tasks.py            # 1111 平台專屬的分類抓取 Celery 任務。
        ├── platform_cakeresume/
        │   ├── parsers.py          # Cakeresume 平台數據轉換純函數，從 __NEXT_DATA__ JSON 和 HTML 內容中提取數據。
        │   ├── strategies.py       # Cakeresume 平台三大策略接口的 HTML 列表抓取和 __NEXT_DATA__ 解析實現。
        │   └── tasks.py            # Cakeresume 平台專屬的分類抓取 Celery 任務。
        └── platform_yes123/
            ├── parsers.py          # Yes123 平台數據轉換純函數。
            ├── strategies.py       # Yes123 平台三大策略接口的傳統 HTML 實現。
            └── tasks.py            # Yes123 平台專屬的分類抓取 Celery 任務。
```

---

## 各模組職責詳解

### 核心框架 (Core Framework) - `crawler/core/`

- **文件 01: `crawler/core/protocols.py`**
  - **職責: 接口藍圖 (Contracts)**。使用 `typing.Protocol` 定義 `UrlFetcher`, `DetailFetcher`, `DetailParser` 三個核心接口。它確保了所有平台特定實現都遵守相同的「契約」，讓它們可以被 Orchestrator 自由替換和調用，是實現策略模式的基石。
- **文件 02: `crawler/core/orchestrator.py`**
  - **職責: 總指揮官 (Orchestrator)**。實現 `CrawlerOrchestrator` 類，負責執行標準化的兩階段（urls -> details）爬取流程。它調度策略、處理併發、管理 Redis 中介快取、捕獲宏觀錯誤並記錄「現場快照」，並優化了 URL 提取和併發任務的錯誤處理，但不關心任何特定平台的實現細節。

### 工廠與配置 (Factory & Configuration)

- **文件 03: `crawler/factory.py`**
  - **職責: 組裝工廠 (Assembly Factory)**。提供 `create_crawler` 函式，作為連接通用框架與特定實現的橋樑。它根據平台名稱，動態地從各平台的 `strategies` 模組中導入並「組裝」正確的策略組件，並支持傳入 `category_ids` 以限定抓取範圍，返回一個完全配置好的 `CrawlerOrchestrator` 實例。
- **文件 04: `crawler/settings.py`**
  - **職責: 唯一配置中心 (Single Source of Truth)**。使用 Pydantic 模型定義所有配置。集中管理資料庫、Celery、Redis 等基礎設施連接信息，以及所有平台特定的參數（如 `max_pages`, `max_workers`, `headers`），確保配置的類型安全和統一管理。

### 平台特定實現 (Platform-Specific Implementations) - `crawler/projects/`

#### 平台 104 (`/platform_104/`)
- **`strategies.py`**: **API 專家**。實現三大接口，策略完全基於 API 進行。
- **`parsers.py`**: **數據翻譯官**。包含將 104 API 返回的 JSON 數據轉換為標準化模型的純函數。
- **`tasks.py`**: **分類抓取器**。定義專屬的 Celery 任務 `run_category_pipeline`，從分類 API 獲取數據，此任務被路由到專用的 `category_queue`。

#### 平台 1111 (`/platform_1111/`)
- **`strategies.py`**: **混合戰術專家**。實現三大接口，策略為「API列表 + HTML詳情」的混合模式。
- **`parsers.py`**: **數據翻譯官**。包含將列表 API 中介數據和詳情頁 HTML 內容，共同轉換為標準化 Job 模型的純函數。
- **`tasks.py`**: **分類抓取器**。同平台 104，定義從 1111 分類 API 獲取數據的 Celery 任務。

#### 平台 Cakeresume (`/platform_cakeresume/`)
- **`strategies.py`**: **前端解析專家**。策略為「HTML列表 + HTML詳情」，特色是從頁面 `<script id="__NEXT_DATA__">` 標籤中解析內嵌的 JSON。
- **`parsers.py`**: **數據翻譯官**。包含從 `__NEXT_DATA__` JSON 和原始 HTML 內容中提取數據並轉換為 Job 模型的純函數。
- **`tasks.py`**: **分類抓取器**。定義專屬的 Celery 任務 `run_category_pipeline`，從 `__NEXT_DATA__` 標籤中獲取分類數據。

#### 平台 Yes123 (`/platform_yes123/`)
- **`strategies.py`**: **傳統HTML專家**。策略為純粹的 HTML 抓取和解析，需特別處理 `big5` 編碼問題。
- **`parsers.py`**: **數據翻譯官**。包含使用 BeautifulSoup 從傳統 HTML 結構中提取信息並轉換為 Job 模型的純函數。
- **`tasks.py`**: **分類抓取器**。定義專屬的 Celery 任務 `run_category_pipeline`，從 API 獲取分類數據。

### 資料庫層 (Database Layer) - `crawler/database/`

- **`__init__.py`**: Python 包初始化文件。
- **`connection.py`**: **連接管家**。負責創建和管理 SQLAlchemy 引擎實例，內含強大的 Tenacity 重試邏輯。
- **`schema.py`**: **數據庫藍圖**。使用 SQLModel 定義 `CategorySource`, `Url`, `Job` 三個核心表的結構。
- **`repository.py`**: **數據庫操作員**。封裝所有對資料庫的 CRUD 操作，實現數據訪問的隔離。

### 異步任務與調度 (Asynchronous Tasks & Scheduling)

- **`app.py`**: **Celery 的大腦**。定義和配置 Celery 應用實例，自動發現任務並設定任務路由。
- **`worker.py`**: **Celery 工人監控器**。用於在 worker 啟動後打印已註冊的任務列表，方便調試。
- **`src/dataflow/etl/crawler.py`**: **Airflow Task 工廠**。提供創建 Airflow Operator 的輔助函數。
- **`src/dataflow/dags/crawler_pipeline.py`**: **Airflow 工作流藍圖**。動態地為所有平台創建 DAGs。

### 通用工具與 API (Common Utilities & API)

- **`__init__.py`**: Python 包初始化文件。
- **`cli.py`**: **開發與維運工具箱**。提供基於 Typer 的強大命令行界面，如 `db init`, `task` (支持指定分類), `debug-url` (支持保存 HTML)。
- **`utils.py`**: **通用工具函式庫**。提供全項目共享的輔助函數，如帶有重試和 `kwargs` 支持的 `make_request`、`clean_text` (清理 HTML 標籤和空白字符) 和 `safe_extract_text` (安全提取 BeautifulSoup 標籤文本)。
- **`enums.py`**: **標準化字典**。定義 `SourcePlatform`, `CrawlStatus` 等枚舉，防止魔術字符串。
- **`cache.py`**: **Redis 客戶端管理器**。以單例模式管理 Redis 連接。
- **`api/`**: **數據查詢 API**。使用 FastAPI 構建，提供查詢已爬取數據的端點。
