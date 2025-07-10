角色 (Role):
你是一位資深的 Python 軟體架構師，專長是設計和建構可擴展、可維護的數據管道和網路爬蟲系統。
你精通「DRY (Don't Repeat Yourself)」原則和「組合優於繼承」的設計哲學，並熟悉使用 Airflow 和 Docker Swarm 進行部署。

任務 (Task):
重構一個現有的多平台職缺爬蟲專案。
目前的專案為每個平台（104, 1111, Cakeresume, Yes123）都編寫了獨立的爬取流程，導致代碼大量重複、難以維護和擴展。
你的任務是將其重構成一個統一的、由策略模式驅動的框架。

核心目標 (Core Objective):
從「為每個平台編寫一套完整流程」轉變為「建立一個通用爬蟲框架，並為每個平台提供可插拔的、特定於平台的策略組件」。

數據庫 Schema 說明 (Database Schema Explanation):
專案使用一個統一的、標準化的數據庫 Schema 來儲存來自所有平台的數據。
*   `tb_category_source` (CategorySource model): 包含 `source_platform`, `source_category_id`, `parent_source_id`。
*   `tb_urls` (Url model): 包含 `source_url` (主鍵), `source` (平台來源), `status` (職缺是否活躍), `details_crawl_status` (爬取狀態: `PENDING`, `COMPLETED`, `FAILED`)。
*   `tb_jobs` (Job model): 包含 `source_platform`, `source_job_id`, `title`, `description`, `location_text`, `salary_min`, `salary_max`, `salary_type`, `job_type`。

設計藍圖與架構要求 (Architectural Blueprint & Requirements):
1.  **核心策略接口 (Core Strategy Interfaces)**:
    *   使用 `typing.Protocol` 定義四個核心接口：`CategoryFetcher`, `UrlFetcher`, `DetailFetcher`, `DetailParser`。
    *   每個接口應該有清晰的職責分離，並且能夠被不同平台的具體實現所覆蓋。
        *   `CategoryFetcher`: 負責獲取一個平台的職務分類資料。接口為 `__call__(self) -> Any`
        *   `UrlFetcher`: 負責獲取一個平台所有職缺的原始資料項（API dict 或 HTML tag），作為生成器逐批 `yield` 原始資料項。
        *   `DetailFetcher`: 負責根據 URL 獲取單一職缺的詳細內容（HTML 或 JSON 字串）。
        *   `DetailParser`: 負責將 `DetailFetcher` 的原始內容和 `UrlFetcher` 的中介資料解析為標準化的 `Job` 模型物件。
            接口為 `__call__(self, raw_content: str, url: str, intermediate_data: Optional[Dict]) -> Optional[Job]`
        
2.  **爬蟲協調器 (Crawler Orchestrator)**:
    *   創建一個 `CrawlerOrchestrator` 類，負責協調各個策略的執行。
    *   它應該能夠接收特定平台的策略組件，並提供統一的執行流程。
        *   `run_category_pipeline()`: 執行分類抓取 pipeline。調用 `CategoryFetcher` 獲取原始分類數據，並同步到資料庫。
        *   `run_urls_pipeline()`: 
                它調用 `UrlFetcher`，遍歷獲取的資料項，提取 URL，
                將原始資料項作為中介資料存入 Redis (KEY: `meta:{platform}:{url}`, EX: 86400s)，
                並調用 `repository.upsert_urls` 將 URL 存入資料庫。
        *   `run_details_pipeline(limit: int)`: 
                它從資料庫獲取待處理的 `Url` 物件，為每個 URL 從 Redis 讀取中介資料，
                然後併發地調用 `DetailFetcher` 和 `DetailParser`。
                並將 URL 狀態標記為 `COMPLETED` 或 `FAILED`，最後批量將成功的 `Job` 物件存入資料庫。
                整個過程必須記錄詳細的錯誤日誌（包含平台、URL 和錯誤信息），
                包含健壯的錯誤處理邏輯（包括解析失敗返回 `None` 的情況），
                ，不應因單點失敗而中斷，且能捕獲單個 URL 的處理失敗。

3.  **工廠模式 (Factory Pattern)**:
    *   使用工廠模式來動態生成 `CrawlerOrchestrator` 實例。
    *   創建 `create_crawler(platform: SourcePlatform) -> CrawlerOrchestrator` 函式，根據平台枚舉，實例化對應的策略組件。

4.  **平台模組重構 (Platform Module Refactoring)**:
    *   對於每個平台，創建新的 `strategies.py` 和 `parsers.py` 文件。
    *   在 `strategies.py` 中實現四個接口協議。 ( `UrlFetcher`, `DetailFetcher`, `DetailParser`, `CategoryFetcher`)
    *   確保 `parsers.py` 只包含純粹的數據轉換邏輯，由 `strategies.py` 調用具體實現數據解析邏輯。
        在 `strategies.py` 中，實現 
        *   純 API (104): `DetailParser` 處理 JSON 字串。
        *   純 HTML (yes123): `DetailParser` 使用 BeautifulSoup 處理 HTML。
        *   特殊 HTML (Cakeresume): `DetailParser` 從 HTML 中找到 `<script>` 標籤並解析其內嵌的 JSON。
        *   混合 API+HTML (1111): `UrlFetcher` 抓取 API，`DetailFetcher` 抓取 HTML，`DetailParser` 
                必須同時利用 `raw_content` (HTML) 和 `intermediate_data` (來自列表API的快取) 進行解析。

5.  **統一的任務調度 (Unified Task Scheduling)**:
    *   使用 Airflow 來統一管理所有平台的爬取任務。
    *   創建一個 `src/dataflow/etl/crawler.py` 文件，用於生成 Airflow tasks。
    *   在 `src/dataflow/dags/crawler_pipeline.py` 中動態生成 DAGs，為每個平台創建一個 DAG。
        *   每個 DAG 的結構為：` {{ category_task >> }}  urls_task >> details_task`。

6.  **通用工具和配置 (Utils & Settings)**:
    *   將各平台通用的輔助函數統一到 `crawler/utils.py`。
    *   確保所有平台的請求都通過 `make_request` 函數，以便集中管理重試、延遲和 User-Agent 等策略。
    *   `settings.py` 應作為所有平台配置（如 `max_pages`, `max_workers`）的唯一來源 (Single Source of Truth)。


輸入文件 (Input Files):
當前專案的完整程式碼庫。

期望的輸出 (Expected Output):
請提供一個完整的、可運行的重構後專案的文件列表和其完整內容。文件結構應清晰地反映上述設計藍圖。
請確保代碼風格一致、註釋清晰，並在關鍵的類和函數上添加 Docstring 解釋其職責。

**開始執行：**
現在，請測試 platform 所有平台，基於這個**簡化的三表模型**，確認 category -> urls -> jobs 所有執行結果都能存到 SQL。
1.  使用docker-compose.yml；如果需要docker logs 來確認，只需要必要的日誌輸出即可。 最多讀取17筆紀錄。 --tail 17
2.  任何文件修改前，先參考demo文件，可以搭配檔案api data or soup網頁原始碼列印。思考三次COT 確認可行方案。
3.  任何文件修改後，使用ruff進行代碼格式化和靜態檢查，確保代碼符合最佳實踐。
4.  執行過程中，請確保所有操作都符合上述架構原則和要求。並且說明目前狀況、採取的解決方法。
5.  問題解決的時候，請描述問題的根源和解決方案，根據檔案格式接續記錄到 QA.md 。
6.  重申一次 修改文件前 請全部預覽完成 COT至少3次 │ 不要一直小打小鬧 一次改好 就是專業

紀錄格式
問題描述：<問題描述 Q-001> 編號從1開始...
解決方案：<解決方案>