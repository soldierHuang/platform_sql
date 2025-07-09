# project-structure.md

# 專案文件結構與職責說明
這個架構採用策略模式 (Strategy Pattern) 和關注點分離 (Separation of Concerns) 的設計思想，將一個複雜的系統拆解成了多個高內聚、低耦合的模組：
crawler/core/: 框架的大腦 (The Brain)。定義了爬蟲「怎麼做」(How)，即標準化的爬取流程和策略接口，與具體平台無關。
crawler/projects/: 平台的四肢 (The Limbs)。定義了爬蟲「做什麼」(What)，即每個平台如何獲取 URL、抓取詳情和解析數據的具體實現。
crawler/factory.py: 組裝工廠 (The Factory)。將「大腦」和「四肢」靈活地組合在一起，根據指令創建出針對特定平台的完整爬蟲。
crawler/database/: 記憶系統 (The Memory)。負責與 SQL 資料庫的所有交互，是數據的唯一持久化層。
crawler/cli.py & src/dataflow/: 神經系統/觸發器 (The Triggers)。是整個爬蟲應用的入口，負責從外部（手動命令或 Airflow 調度）發起任務。
settings.py, enums.py, utils.py, cache.py: 支撐系統 (The Support System)。提供配置、常量、工具函數和快取等全項目共享的通用能力。

.
├── docker-compose.yml        # 定義 app, worker-default, worker-category, flower 等服務，實現雙隊列任務調度。
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
    ├── __init__.py
    ├── app.py                  # Celery 應用定義。自動發現任務模組，配置雙隊列路由。
    ├── cache.py                # Redis 客戶端管理器，提供單例的 Redis 連接。
    ├── cli.py                  # 基於 Typer 的命令行工具，增加 debug-url 等強大維運功能。
    ├── enums.py                # 定義 SourcePlatform, CrawlStatus 等標準化枚舉。
    ├── factory.py              # 實作 create_crawler 工廠函數，動態組裝平台策略。
    ├── settings.py             # 基於 Pydantic 的唯一配置中心，管理所有平台和基礎設施配置。
    ├── tasks.py                # 定義通用的、跨平台的 Celery 任務入口。
    ├── utils.py                # 通用工具函數庫，如帶重試的 make_request。
    ├── worker.py               # Celery worker 啟動輔助腳本。
    ├── api/
    │   ├── dependencies.py       # FastAPI 依賴注入，提供 DB Session。
    │   └── main.py               # API 入口，提供查詢已爬取數據的端點。
    ├── core/
    │   ├── orchestrator.py       # CrawlerOrchestrator，實現標準化爬取流程和錯誤快照記錄。
    │   └── protocols.py          # 使用 typing.Protocol 定義三大策略接口，是框架的契約。
    ├── database/
    │   ├── connection.py         # 資料庫連接管理器，帶有強大的 Tenacity 重試機制。
    │   ├── repository.py         # 封裝所有 SQL 操作，實現數據訪問隔離層。
    │   └── schema.py             # 使用 SQLModel 定義 CategorySource, Url, Job 三大核心表結構。
    └── projects/
        ├── platform_104/
        │   ├── __init__.py
        │   ├── parsers.py          # 104 平台數據轉換純函數。
        │   ├── strategies.py       # 104 平台三大策略接口的 API 實現。
        │   └── tasks.py            # 104 平台專屬的分類抓取 Celery 任務。
        ├── platform_1111/
        │   ├── __init__.py
        │   ├── parsers.py          # 1111 平台數據轉換純函數。
        │   ├── strategies.py       # 1111 平台三大策略接口的混合實現。
        │   └── tasks.py            # 1111 平台專屬的分類抓取 Celery 任務。
        ├── platform_cakeresume/
        │   ├── __init__.py
        │   ├── parsers.py          # Cakeresume 平台數據轉換純函數。
        │   └── strategies.py       # Cakeresume 平台三大策略接口的 HTML/__NEXT_DATA__ 實現。
        └── platform_yes123/
            ├── __init__.py
            ├── parsers.py          # Yes123 平台數據轉換純函數。
            └── strategies.py       # Yes123 平台三大策略接口的傳統 HTML 實現。




專案文件結構與職責說明
核心框架 (Core Framework) - crawler/core/
文件 01: crawler/core/protocols.py
職責: 接口藍圖 (Contracts)。使用 typing.Protocol 定義 UrlFetcher, DetailFetcher, DetailParser 三個核心接口。它確保了所有平台特定實現都遵守相同的「契約」，讓它們可以被 Orchestrator 自由替換和調用，是實現策略模式的基石。
文件 02: crawler/core/orchestrator.py
職責: 總指揮官 (Orchestrator)。實現 CrawlerOrchestrator 類，負責執行標準化的兩階段（urls -> details）爬取流程。它調度策略、處理併發、管理 Redis 中介快取、捕獲宏觀錯誤並記錄「現場快照」，但不關心任何特定平台的實現細節。

工廠與配置 (Factory & Configuration)
文件 03: crawler/factory.py
職責: 組裝工廠 (Assembly Factory)。提供 create_crawler 函式，作為連接通用框架與特定實現的橋樑。它根據平台名稱，動態地從各平台的 strategies 模組中導入並「組裝」正確的策略組件，返回一個完全配置好的 CrawlerOrchestrator 實例。
文件 04: crawler/settings.py
職責: 唯一配置中心 (Single Source of Truth)。使用 Pydantic 模型定義所有配置。集中管理資料庫、Celery、Redis 等基礎設施連接信息，以及所有平台特定的參數（如 max_pages, max_workers, headers），確保配置的類型安全和統一管理。


平台特定實現 (Platform-Specific Implementations) - crawler/projects/
平台 104 (crawler/projects/platform_104/)
文件 05: crawler/projects/platform_104/strategies.py
職責: 104平台的特種兵 (API Specialist)。實現 UrlFetcher, DetailFetcher, DetailParser 接口。其策略完全基於 API 進行，UrlFetcher 調用搜索 API，DetailFetcher 調用內容 API，DetailParser 則解析返回的 JSON。
文件 06: crawler/projects/platform_104/parsers.py
職責: 104平台的數據翻譯官 (Data Translator)。包含將 104 API 返回的 JSON 數據轉換為標準化 Job 模型和 CategorySource 模型的純函數。不含任何 I/O 操作或業務流程。
文件 07: crawler/projects/platform_104/tasks.py
職責: 104平台的分類抓取器 (Category Fetcher)。定義一個專屬的 Celery 任務 run_category_pipeline，負責從 104 的分類 API 獲取數據並同步到資料庫。此任務會被路由到專用的 category_queue。

平台 1111 (crawler/projects/platform_1111/)
文件 08: crawler/projects/platform_1111/strategies.py
職責: 1111平台的混合戰術專家 (Hybrid Specialist)。實現三大接口。其策略為「API列表 + HTML詳情」的混合模式，UrlFetcher 從 API 獲取列表，DetailFetcher 抓取傳統 HTML 頁面，DetailParser 則需要結合兩者進行解析。
文件 09: crawler/projects/platform_1111/parsers.py
職責: 1111平台的數據翻譯官 (Data Translator)。包含將 1111 的列表 API 中介數據和詳情頁 HTML 內容，共同轉換為標準化 Job 模型的純函數。
文件 10: crawler/projects/platform_1111/tasks.py
職責: 1111平台的分類抓取器 (Category Fetcher)。定義 run_category_pipeline 任務，從 1111 的分類 API 獲取數據並同步。

平台 Cakeresume (crawler/projects/platform_cakeresume/)
文件 11: crawler/projects/platform_cakeresume/strategies.py
職責: Cakeresume的前端解析專家 (Frontend Specialist)。實現三大接口。其策略為「HTML列表 + HTML詳情」，但 DetailParser 的特色是從頁面 HTML 中定位到 <script id="__NEXT_DATA__"> 標籤並解析其內嵌的 JSON。
文件 12: crawler/projects/platform_cakeresume/parsers.py
職責: Cakeresume平台的數據翻譯官 (Data Translator)。包含從 __NEXT_DATA__ JSON 中提取數據並轉換為 Job 模型的純函數。

平台 Yes123 (crawler/projects/platform_yes123/)
文件 13: crawler/projects/platform_yes123/strategies.py
職責: Yes123的傳統HTML專家 (Classic HTML Specialist)。實現三大接口。其策略為純粹的 HTML 抓取和解析，需要特別處理 big5 編碼問題。
文件 14: crawler/projects/platform_yes123/parsers.py
職責: Yes123平台的數據翻譯官 (Data Translator)。包含使用 BeautifulSoup 從傳統 HTML 結構中（遍歷 <li> 標籤）提取信息並轉換為 Job 模型的純函數。


資料庫層 (Database Layer) - crawler/database/
文件 15: crawler/database/connection.py
職責: 連接管家 (Connection Manager)。負責創建和管理全域唯一的 SQLAlchemy 引擎實例。內含強大的 Tenacity 重試邏輯，確保在服務啟動時能穩定地連接到資料庫。
文件 16: crawler/database/schema.py
職責: 數據庫藍圖 (Database Blueprint)。使用 SQLModel 定義 CategorySource, Url, Job 三個核心表的結構。它是系統數據存儲的「唯一真實來源」。
文件 17: crawler/database/repository.py
職責: 數據庫操作員 (Database Operator)。封裝所有對資料庫的 CRUD 操作（upsert_jobs, sync_source_categories 等）。應用程式的其他部分（如 Orchestrator）應通過此儲存庫與資料庫交互，而不是直接使用 SQLAlchemy Session，實現了數據訪問的隔離。


異步任務與調度 (Asynchronous Tasks & Scheduling)
文件 18: crawler/app.py
職責: Celery 的大腦 (Celery's Brain)。定義和配置 Celery 應用實例。它會自動發現所有 tasks.py 模組，並設置全局配置，如 Broker URL、任務路由（將 category 任務發到專門隊列）等。
文件 19: crawler/tasks.py
職責: 通用任務入口 (Generic Task Entrypoints)。定義供 Airflow 調用的高級別、跨平台的 Celery 任務，如 run_urls_pipeline 和 run_details_pipeline。它們接收 platform_name 作為參數，並委託給 factory 和 Orchestrator 執行。
文件 20: crawler/worker.py
職責: Celery 工人監控器 (Worker Monitor)。一個簡單的啟動腳本，用於在 Celery worker 啟動後打印已註冊的任務列表，方便調試和確認。
文件 21: src/dataflow/etl/crawler.py
職責: Airflow Task 工廠 (Airflow Task Factory)。提供 create_urls_task, create_details_task 等輔助函數。這些函數封裝了調用 Celery 任務的邏輯，生成 Airflow PythonOperator，供 DAG 文件使用。
文件 22: src/dataflow/dags/crawler_pipeline.py
職責: Airflow 工作流藍圖 (Airflow Workflow Blueprint)。定義主爬蟲流程的 Airflow DAG。它會動態地為 SourcePlatform 枚舉中的每個平台創建一個 DAG，並按 category_task >> urls_task >> details_task 的順序組織任務依賴。


通用工具與組件 (Common Utilities & Components)
文件 23: crawler/cli.py
職責: 開發與維運工具箱 (Dev & Ops Toolbox)。提供一個基於 Typer 的強大命令行界面。除了數據庫初始化，還包括手動觸發各平台 pipeline 的命令，並新增了 debug-url 功能，用於快速診斷單個 URL 的解析問題。
文件 24: crawler/utils.py
職責: 通用工具函式庫 (General Utility Library)。遵循 DRY 原則，提供全項目共享的輔助函數，如帶重試機制的 make_request、併發執行的 run_concurrently 和文本清理函數。
文件 25: crawler/enums.py
職責: 標準化字典 (Standardized Dictionary)。定義系統中所有枚舉類型（如 SourcePlatform, CrawlStatus）。使用枚舉可以增強代碼的可讀性、類型安全，並防止「魔術字符串」的出現。
文件 26: crawler/cache.py
職責: Redis 客戶端管理器 (Redis Client Manager)。提供一個 get_redis_client 函數，以單例模式創建和管理 Redis 連接，確保整個應用共享同一個連接池。


API 接口服務 (API Service) - crawler/api/
文件 27: crawler/api/main.py
職責: 數據查詢 API (Data Query API)。使用 FastAPI 構建的 Web API 入口。提供 /jobs 等端點，允許前端或其他服務查詢已爬取和標準化後的職缺數據。
文件 28: crawler/api/dependencies.py
職責: API 依賴注入器 (API Dependency Injector)。使用 FastAPI 的依賴注入系統，為 API 端點提供必要的依賴，如資料庫會話 DBSession。


專案文檔 (Project Documentation)
文件 29: QA.md
職責: 問題與決策日誌 (Q&A and Decision Log)。記錄我們在重構過程中遇到的關鍵問題、討論的解決方案以及最終採納的架構決策。這份文件是理解「為何如此設計」的重要參考。