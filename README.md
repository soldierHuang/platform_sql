# 職缺數據採集與分析系統

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/) [![Docker](https://img.shields.io/badge/Docker-20.10-blue.svg)](https://www.docker.com/) [![Celery](https://img.shields.io/badge/Celery-5.3-green.svg)](http://www.celeryproject.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一個現代化、可擴展的多平台職缺數據採集系統，採用策略模式進行設計，並透過 Docker Swarm 進行高可用性部署。

---

## 主要特色

- **策略模式驅動**：將各平台獨特的抓取、解析邏輯封裝成獨立的策略組件，易於擴展與維護。
- **兩階段爬取流程**：將「URL 列表抓取」與「職缺詳情抓取」解耦，提升系統的穩定性與容錯能力。
- **多平台支援**：內建支援 104、1111、Yes123、Cakeresume 等主流招聘平台。
- **容器化架構**：使用 Docker 和 Docker Compose 進行環境標準化，確保開發與生產環境一致。
- **高可用性部署**：提供 Docker Swarm 部署方案，支援服務的自動重啟、擴展與負載均衡。
- **豐富的管理工具**：整合 Flower、RabbitMQ Management、phpMyAdmin 等工具，方便監控與管理。

---

## 系統架構

本系統採用微服務架構，各組件職責分明，透過消息隊列與快取進行非同步協作。

![系統架構圖](./crawler/plantform_architure.mmd)
![資料蒐集流程](./crawler/plantform_architure.mmd)


---

## 部署與操作指南

本專案支援兩種主要的部署模式：本地開發用的 `Docker Compose` 和生產環境用的 `Docker Swarm`。

### 模式一：本地開發環境 (Docker Compose)

此模式適用於日常開發、功能測試與偵錯。

1.  **環境準備**
    - 確認已安裝 [Docker](https://www.docker.com/products/docker-desktop/) 及 Docker Compose。
    - 根據 `.env.example` 檔案建立一份 `.env` 檔案，並填寫必要的環境變數。

2.  **啟動服務**
    ```bash
    # 此指令會建置映像檔，並在背景啟動所有服務
    docker compose up --build -d
    ```

3.  **初始化資料庫**
    首次啟動或清空資料庫後，必須執行此指令來建立資料表。
    ```bash
    docker compose exec app python -m crawler.cli db init
    ```

> **需要更詳細的本地開發指令嗎？**
> 包含各平台功能測試、資料庫檢查、日常維護等詳細步驟，請參考：
> #### [📄 v1_crawler_local_to_docker.md](./v1_crawler_local_to_docker.md)

### 模式二：生產環境部署 (Docker Swarm)

此模式利用 Docker Swarm 的叢集管理能力，提供服務的高可用性與擴展性。

1.  **環境準備**
    - 確認您的 Docker 環境已啟用 Swarm 模式。

2.  **初始化 Swarm**
    在管理節點 (Manager Node) 上執行初始化。
    ```bash
    # Docker 會自動偵測 IP，若有多網卡主機請依提示手動指定
    docker swarm init
    ```

3.  **部署應用程式堆疊 (Stack)**
    ```bash
    # -c 指定 stack 設定檔，最後為 stack 名稱
    docker stack deploy -c docker_stack.yml crawler_main_stack
    ```

> **需要更詳細的 Swarm 部署與維護指令嗎？**
> 包含服務狀態檢查、功能測試、線上偵錯等詳細步驟，請參考：
> #### [📄 v2_docker_to_swarm.md](./v2_docker_to_swarm.md)

---

## 目錄結構

```
project_104_gemini/
├── crawler/                # 應用程式核心目錄
│   ├── api/                # FastAPI 相關模組
│   ├── app.py              # Celery App 實例
│   ├── cache.py            # Redis 快取客戶端
│   ├── cli.py              # Typer CLI 指令入口
│   ├── core/               # 爬蟲核心 (Orchestrator, Protocols)
│   ├── database/           # 資料庫模組 (Connection, Repository, Schema)
│   ├── enums.py            # 專案用枚舉
│   ├── factory.py          # 爬蟲工廠，用於動態生成實例
│   ├── projects/           # 各平台實作目錄
│   │   ├── platform_104/
│   │   ├── platform_1111/
│   │   ├── platform_cakeresume/
│   │   └── platform_yes123/
│   ├── settings.py         # Pydantic-Settings 設定檔
│   └── utils.py            # 共用工具函數
├── demo/                   # 測試用的資料與腳本
├── src/                    # Airflow DAGs 與相關 ETL 腳本
│   └── dataflow/
├── .env                    # 環境變數檔 (需自行創建)
├── .env.example            # 環境變數檔範例
├── docker-compose.yml      # Docker Compose 主要設定檔
├── docker_stack.yml        # Docker Swarm 部署設定檔
├── Dockerfile              # 應用程式 Docker 映像檔定義
├── README.md               # 就是本文件
└── ... (其他設定檔)
```

---

## 授權 (License)

本專案採用 [MIT License](https://opensource.org/licenses/MIT) 授權。
