# 職缺數據採集系統

## 專案總覽 (Project Overview)

本專案是一個為大規模、多平台職缺數據採集而設計的分布式爬蟲系統。它採用了現代化的 Python 技術棧和微服務架構，旨在實現高可用性、可擴展性、和可維護性。

**核心技術棧:**
- **應用程式:** Python 3.11
- **容器化與編排:** Docker, Docker Compose
- **異步任務隊列:** Celery
- **訊息代理 (Broker):** RabbitMQ
- **結果後端 & 快取:** Redis
- **核心資料庫:** MySQL 8.0
- **Web API 框架:** FastAPI
- **CLI 框架:** Typer
- **配置管理:** Pydantic-Settings
- **資料庫互動:** SQLModel (基於 SQLAlchemy 和 Pydantic)

## 核心架構 (Core Architecture)

本專案遵循「職責分離」和「組合優於繼承」的設計哲學。

### 組件職責 (Component Responsibilities)

- **MySQL (核心數據庫):** 作為系統的「黃金數據源」，儲存所有經過清洗和解析的、結構化的、需要長期持久化的核心數據。
- **Redis (中繼快取):** 扮演通用中繼數據快取層的角色。主要用於在不同任務階段之間傳遞**臨時的、輔助性的、可犧牲的**數據。例如，在抓取列表頁時，會將順帶獲取的職缺部分元數據（如薪資、公司名）存入 Redis，供後續的詳情頁抓取任務直接使用，以減少不必要的二次請求。
- **RabbitMQ (訊息代理):** 作為 Celery 的訊息中介，負責接收、儲存和轉發任務訊息，是解耦任務發布者和執行者的關鍵。
- **Celery Workers (任務執行者)::** 真正執行數據採集和處理的背景工作單元。每個平台（如 104, 1111）都有專屬的 Worker 和獨立的任務隊列（如 `queue_104`），實現資源隔離和定向任務分派。
- **API (FastAPI):** 提供一個 HTTP 接口，用於觸發任務、查詢狀態或未來可能的外部系統整合。
- **Flower (監控儀表板):** 一個基於 Web 的 Celery 監控工具，用於實時查看 Worker 狀態、任務隊列和執行結果。

### 數據流程 (Data Flow)

系統的數據採集遵循一個標準的三階段流程，這個流程清晰地體現了 Redis 作為中繼快取的作用。

```plantuml
@startuml
skinparam sequenceArrowThickness 2
skinparam roundcorner 20
skinparam maxmessagesize 150
skinparam sequenceParticipant bold

actor User as "開發者/排程器"
participant "CLI / API" as Cli
participant "Celery Broker
(RabbitMQ)" as Broker
participant "Celery Worker" as Worker
participant "Redis" as Cache
participant "MySQL" as DB

User -> Cli: 觸發 `run_urls_pipeline`
Cli -> Broker: 發送 `run_urls_pipeline` 任務
Broker -> Worker: 分派任務

activate Worker
Worker -> Worker: 執行 `_UrlFetcher` 抓取列表頁
Worker -> Cache: **[核心]** 將列表頁的元數據 (metadata) 存入 Redis 快取
Worker -> DB: 將新的職缺 URL 存入 `tb_urls`

User -> Cli: 觸發 `run_details_pipeline`
Cli -> Broker: 發送 `run_details_pipeline` 任務
Broker -> Worker: 分派任務

Worker -> DB: 讀取 `tb_urls` 中待處理的 URL
Worker -> Cache: **[核心]** 優先嘗試讀取該 URL 的元數據快取
alt 找到快取
    Cache --> Worker: 返回元數據
else 未找到快取
    Cache --> Worker: 返回空值
end

Worker -> Worker: 執行 `_DetailFetcher` 抓取詳情頁 HTML/API
Worker -> Worker: 結合元數據和詳情頁內容，執行 `parser`
Worker -> DB: **[核心]** 將完整的結構化數據寫入 `tb_jobs` 等核心七表
Worker -> DB: 更新 `tb_urls` 的處理狀態
deactivate Worker

@enduml
```

## 簡化的三表模型詳解 (Simplified Three-Table Model Details)

本專案第一階段採用簡化的三表數據模型，以快速驗證核心採集流程。

*   **`tb_category_source` (平台原始類別表):**
    *   **職責:** 只負責記錄從各個平台抓取到的原始職務類別信息。
    *   **核心欄位:** `id`, `source_platform`, `source_category_id`, `source_category_name`, `parent_source_id`。
    *   **第一階段作用:** 作為 `urls` 任務的觸發依據。例如，我們可以指定「抓取 104 平台下，`source_category_id` 為 '2007001000' 的所有職缺」。

*   **`tb_urls` (職缺 URL 表):**
    *   **職責:** 追蹤所有被發現的職缺 URL 及其處理狀態和生命週期。
    *   **核心欄位:** `source_url`, `source`, `status`, `details_crawl_status`。
    *   **第一階段作用:** 作為 `details` 任務的工作隊列，並記錄每個 URL 的抓取進度。

*   **`tb_jobs` (職缺詳情表):**
    *   **職責:** 存儲從各平台解析後的職缺詳細資料。
    *   **核心欄位:** `id`, `source_platform`, `source_job_id`, `url`, `title`, `description`, `salary_text` 等標準化欄位。
    *   **第一階段作用:** 作為數據採集的最終產出。

## 目錄結構 (Directory Structure)

```
/home/soldier/project_104_gemini/
├── .env                    # 核心配置文件，儲存所有密鑰和環境變數
├── docker-compose.yml      # Docker Compose 基礎服務定義
├── docker-compose.dev.yml  # 開發環境專用的覆蓋配置
├── Dockerfile              # 應用程式的 Docker 映像檔建置腳本
├── requirements.txt        # Python 相依套件列表
├── README.md               # (本文件) 專案操作手冊
└── crawler/                # 專案主程式碼目錄
    ├── app.py              # Celery App 實例化與核心配置
    ├── worker.py           # Celery Worker 入口，負責載入任務和初始化
    ├── cli.py              # Typer CLI 指令入口
    ├── settings.py         # Pydantic 配置模型，從 .env 載入設定
    ├── cache.py            # Redis 客戶端初始化
    ├── enums.py            # 專案中使用的所有枚舉類型
    ├── utils.py            # 通用輔助函式 (如併發執行器)
    ├── api/                # FastAPI 相關程式碼
    ├── database/           # 資料庫相關模組
    │   ├── connection.py   # 資料庫連線與初始化
    │   ├── repository.py   # 數據倉儲層，封裝所有資料庫操作
    │   └── schema.py       # 核心三表模型的 SQLModel 定義
    └── projects/           # 各個採集平台的獨立實作
        ├── platform_104/
        ├── platform_1111/
        ├── platform_cakeresume/
        └── platform_yes123/
            ├── tasks.py    # 該平台的所有 Celery 任務定義
            └── parsers.py  # 負責將原始數據轉換為資料庫模型的解析器
```

## 環境設置與啟動步驟 (Setup & Usage)

### 1. 配置環境變數

專案啟動前，必須先建立 `.env` 檔案。您可以從 `.env.example` (如果存在) 複製，或手動建立。確保以下變數已正確填寫：

```bash
# 資料庫設定
MYSQL_ROOT_PASSWORD=your_strong_root_password
MYSQL_DATABASE=job_data
MYSQL_USER=user
MYSQL_PASSWORD=your_strong_user_password

# RabbitMQ 設定
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest

# 本機端口映射 (可選)
MYSQL_EXPOSE_PORT=3306
RABBITMQ_EXPOSE_PORT=5672
RABBITMQ_MGMT_EXPOSE_PORT=15672
API_EXPOSE_PORT=8000
FLOWER_EXPOSE_PORT=5555
PHPMYADMIN_EXPOSE_PORT=8080
```

### 2. 啟動所有服務

使用 Docker Compose V2 指令，同時載入基礎和開發設定檔來啟動所有服務。`--build` 參數會確保在程式碼變更後重新建置映像檔。

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 3. 驗證服務狀態

執行以下指令檢查所有容器是否都處於 `Up` 或 `healthy` 狀態。

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

您應該會看到 `api`, `flower`, `mysql`, `phpmyadmin`, `rabbitmq`, `redis`, `worker-104`, `worker-1111` 等服務都已成功啟動。

## 主要工作流程 (Key Workflows)

### 執行數據採集

所有任務都應透過 `crawler/cli.py` 中定義的指令來觸發。首先，進入 `api` 服務的容器中：

```bash
docker compose exec api bash
```

進入容器後，您可以使用 `python -m crawler.cli` 來執行指令。以下是執行各平台數據採集任務的範例：

```bash
# 初始化資料庫 (只需執行一次，或在資料庫結構變更後執行)
python -m crawler.cli db init

# 執行特定平台的 category 任務 (例如: platform_104)
python -m crawler.cli task run platform_104 category

# 執行特定平台的完整爬取任務 (例如: platform_104)
# 這會同時執行 URL 抓取和詳情頁解析
python -m crawler.cli task run platform_104 crawl

# 您也可以為 crawl 任務指定來源類別ID
# python -m crawler.cli task run platform_104 crawl --sc "2007001000"
```

### 新增一個採集平台

遵循專案的組合模式，新增一個平台非常簡單：

1.  **建立目錄:** 在 `crawler/projects/` 下建立一個新目錄，例如 `platform_yoursite`。
2.  **建立模組:** 在新目錄中建立 `tasks.py` 和 `parsers.py` 檔案。
3.  **實作邏輯:** 參考 `platform_104` 或 `platform_1111` 的結構，在新檔案中實作該平台的抓取和解析邏輯。
4.  **新增 Worker:** 在 `docker-compose.yml` 中，複製一個現有的 worker 服務，並將其名稱和 `-Q` (隊列) 參數更改為新平台的名稱 (例如 `worker-yoursite`, `-Q queue_yoursite`)。
5.  **新增配置:** 在 `crawler/settings.py` 中為新平台新增一個設定類別。
6.  **新增枚舉:** 在 `crawler/enums.py` 的 `SourcePlatform` 中加入新平台的枚舉值。
7.  **重新啟動:** 執行 `docker compose up -d --build` 來使所有變更生效。

## 系統監控 (Monitoring)

### Flower 儀表板

-   **URL:** `http://localhost:5555`
-   **功能:** 在此儀表板上，您可以實時監控所有 Celery Worker 的健康狀況、查看正在執行的任務、已完成的任務、任務的詳細參數和結果，以及各個任務隊列的負載情況。

### MySQL 資料庫監控 (phpMyAdmin)

-   **URL:** `http://localhost:8080`
-   **功能:** phpMyAdmin 是一個基於 Web 的 MySQL 資料庫管理工具。您可以登入 (使用 `.env` 中配置的 `MYSQL_USER` 和 `MYSQL_PASSWORD`)，瀏覽資料庫結構、查看表數據、執行 SQL 查詢，以及監控資料庫的運行狀態。

### Redis 快取監控

-   **方法:** 透過 `redis-cli` 命令列工具直接連接 Redis 容器進行監控。
-   **步驟:**
    1.  進入 Redis 容器：`docker compose exec redis redis-cli`
    2.  常用命令：
        -   `ping`: 檢查 Redis 服務是否運行。
        -   `info memory`: 查看記憶體使用情況。
        -   `dbsize`: 查看當前資料庫中的鍵數量。
        -   `keys *`: 列出所有鍵 (在生產環境中應謹慎使用，可能影響性能)。
        -   `get <key>`: 獲取指定鍵的值。

### RabbitMQ 訊息代理監控

-   **URL:** `http://localhost:15672`
-   **功能:** RabbitMQ Management Plugin 提供了一個 Web 介面，用於監控 RabbitMQ 服務。您可以登入 (使用 `.env` 中配置的 `RABBITMQ_DEFAULT_USER` 和 `RABBITMQ_DEFAULT_PASS`)，查看連接、通道、交換器、隊列的狀態，以及訊息的流動情況。

### 查看服務日誌

如果需要對特定服務進行除錯，可以使用以下指令查看其日誌：

```bash
# 查看 worker-104 的日誌
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs worker-104

# 持續追蹤 api 服務的日誌
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api
```