# 本地開發環境部署指南 (Docker Compose)

本文件旨在引導開發者使用 Docker Compose 在本地快速啟動、測試及維護爬蟲應用程式。

---

## 一、 環境快速啟動

使用以下指令來管理本地的開發環境。

### 1. 啟動所有服務
此指令會根據 `docker-compose.yml` 的定義，在後台建立並啟動所有服務。如果 Docker image 不存在或有更新，`--build` 參數會自動進行建置。

```bash
docker compose up --build -d
```

### 2. 檢查服務狀態
執行後，用此指令確認所有服務容器都處於 `running` 或 `healthy` 狀態。

```bash
docker compose ps
```

### 3. 關閉並清理環境
此指令會停止並移除所有容器。`-v` 參數會一併刪除相關的數據卷 (volume)，**這將會清空您的資料庫**，適用於需要一個全新環境的場景。

```bash
docker compose down -v
```

---

## 二、 訪問管理工具

環境啟動後，可以透過瀏覽器訪問以下內建的管理工具，方便監控與偵錯。

| 工具 | 用途 | 訪問地址 | 預設帳號 | 預設密碼 |
| :--- | :--- | :--- | :--- | :--- |
| **API (FastAPI)** | 查看 API 文檔和進行交互式測試 | [http://localhost:8000/docs](http://localhost:8000/docs) | - | - |
| **Flower** | 監控 Celery Worker 和任務狀態 | [http://localhost:5555](http://localhost:5555) | - | - |
| **RabbitMQ Mgmt** | 查看消息隊列的詳細狀態 | [http://localhost:15672](http://localhost:15672) | `guest` | `guest` |
| **phpMyAdmin** | 圖形化管理 MySQL 資料庫 | [http://localhost:8080](http://localhost:8080) | `root` | `root_password` |
| **Portainer** | 圖形化管理 Docker 環境 | [http://localhost:9000](http://localhost:9000) | (首次需設定) | (首次需設定) |

---

## 三、 核心功能測試

在服務啟動後，執行以下指令以驗證應用程式的核心爬取功能。

### 1. 資料庫初始化
這是**必須執行**的第一步，它會在資料庫中創建所有必要的資料表。

```bash
docker compose exec app python -m crawler.cli db init
```

### 2. 逐一測試各平台功能
以下指令將為每個平台模擬一次完整的爬取流程 (職業分類 -> 網址 -> 頁面資料)。

#### Platform 104
```bash
docker compose exec app celery -A crawler.app call platform_104.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_104 --category-id 2007001001
docker compose exec app python -m crawler.cli task details platform_104 --limit 5
```

#### Platform 1111
```bash
docker compose exec app celery -A crawler.app call platform_1111.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_1111 --category-id 140100
docker compose exec app python -m crawler.cli task details platform_1111 --limit 5
```

#### Platform Yes123
```bash
docker compose exec app celery -A crawler.app call platform_yes123.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_yes123 --category-id '2_1001_0001_0003'
docker compose exec app python -m crawler.cli task details platform_yes123 --limit 5
```

#### Platform Cakeresume
```bash
docker compose exec worker-category celery -A crawler.app call platform_cakeresume.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_cakeresume --category-id 'it_software-engineer'
docker compose exec app python -m crawler.cli task details platform_cakeresume --limit 5
```

---

## 四、 資料庫互動與檢查

提供直接操作資料庫以進行數據驗證的方法。

### 1. 進入 MySQL 容器
```bash
docker compose exec mysql bash
```

### 2. 連接資料庫
進入容器後，使用以下指令連接到 `job_data` 資料庫。
```bash
mysql -uuser -ppassword job_data
```

### 3. 常用查詢範例
```sql
-- 查看各表結構與內容
SELECT * FROM tb_category_source LIMIT 1\G
SELECT * FROM tb_urls LIMIT 1\G
SELECT * FROM tb_jobs LIMIT 1\G

-- 查看最新抓取的 5 筆 URL 狀態
SELECT source, details_crawl_status, source_url FROM tb_urls ORDER BY crawled_at DESC LIMIT 5;

-- 計算特定平台的 URL 數量
SELECT COUNT(*) FROM tb_urls WHERE source = 'platform_104';
```

---

## 五、 日常開發與維護

### 1. 重啟服務以應用程式碼變更
當您修改了 Python 程式碼後，需要重啟 Celery worker 服務來加載新的程式碼。

```bash
docker compose restart worker-default worker-category
```

### 2. 清理 Docker 資源
以下指令可以幫助您釋放磁碟空間。

```bash
# 移除所有未被使用的 Docker Volume (數據卷)
# 警告：此操作會刪除未與任何容器關聯的數據，請謹慎使用！
docker volume rm $(docker volume ls -q)

# 移除所有懸空 (dangling) 的 Docker Image (沒有標籤的 image)
docker rmi $(docker images -f "dangling=true" -q)
```
