# Docker Swarm 與 Airflow 自動化部署維護指南

本文件旨在引導使用者在 Docker Swarm 環境中，部署一個由 Airflow 驅動的全自動化爬蟲應用程式。

---

## 一、 環境初始化 (首次設定)

此章節涵蓋首次設定 Docker Swarm 及所需網路環境的步驟。

### 1. 初始化 Swarm 叢集
將您的 Docker 環境初始化為 Swarm 模式。

```bash
# 如果您的主機擁有多個網路介面，請明確指定 IP
# docker swarm init --advertise-addr <您的主機IP>

# 若為單一網路介面，可讓 Docker 自動偵測
docker swarm init
```

### 2. 創建共享覆蓋網路 (Overlay Network)
建立一個供爬蟲應用程式 (`crawler_main_stack`) 與 Airflow (`airflow_stack`) 之間共享的網路。

```bash
docker network create --driver overlay --attachable crawler_net
```

---

## 二、 應用程式部署

本系統包含兩個核心堆疊 (Stack)，需要依次部署。

### 1. 部署核心爬蟲應用程式
此堆疊包含爬蟲 Worker、API、資料庫等核心服務。

```bash
docker stack deploy -c docker_stack.yml crawler_main_stack
```

### 2. 部署 Airflow 自動化排程器
此堆疊包含 Airflow Webserver、Scheduler 及後端資料庫。

#### a. 建立 Airflow Docker 映像
根據最新的程式碼建立或更新 Airflow 映像。

```bash
docker build -f dockerfile.airflow -t benitorhuang/airflow-crawler:0.0.1 .
```

#### b. 部署 Airflow 堆疊
```bash
docker stack deploy -c docker_airflow.yml airflow_stack
```

### 3. 檢查部署狀態
執行後，用此指令確認所有服務容器都處於 `Running` 狀態。

```bash
# 查看 crawler_main_stack 的服務狀態
docker stack ps crawler_main_stack

# 查看 airflow_stack 的服務狀態
docker stack ps airflow_stack
```

---

## 三、 Airflow 首次啟動設置

在 **首次部署** 或 **資料庫被清除** 後，必須執行以下初始化步驟。

### 1. 找到 Airflow Webserver 容器 ID
```bash
AIRFLOW_WEBSERVER_CONTAINER_ID=$(docker ps --filter "name=airflow_stack_airflow-webserver" -q | head -n 1)
echo "找到 Airflow Webserver 容器 ID: $AIRFLOW_WEBSERVER_CONTAINER_ID"
```

### 2. 初始化 Airflow 元數據資料庫
此指令會在 Airflow 的後端資料庫 (Postgres) 中建立必要的資料表。

```bash
docker exec $AIRFLOW_WEBSERVER_CONTAINER_ID airflow db migrate
```

### 3. 創建 Airflow 管理員帳號
此指令將創建一個用於登入 Airflow UI 的管理員帳號。

```bash
docker exec $AIRFLOW_WEBSERVER_CONTAINER_ID airflow users create \
    --username admin \
    --firstname Airflow \
    --lastname Admin \
    --role Admin \
    --email admin@example.com \
    -p admin
```
> **提示:** 上述指令創建了帳號 `admin`，密碼為 `admin`。

---

## 四、 系統驗證與日常使用

### 1. 訪問管理工具
環境啟動後，可以透過瀏覽器訪問以下管理工具。

| 工具 | 用途 | 訪問地址 | 預設帳號 | 預設密碼 |
| :--- | :--- | :--- | :--- | :--- |
| **Airflow UI** | **核心**：監控、觸發、管理所有爬蟲 DAGs | [http://localhost:8080](http://localhost:8080) | `admin` | `admin` |
| **Flower** | 監控 Celery Worker 和即時任務狀態 | [http://localhost:5555](http://localhost:5555) | - | - |
| **phpMyAdmin** | 圖形化管理爬取到的 MySQL 資料 | [http://localhost:8081](http://localhost:8081) | `root` | `root_password` |
| **Portainer** | 圖形化管理 Docker Swarm 環境 | [http://localhost:9000](http://localhost:9000) | (首次需設定) | (首次需設定) |

### 2. 啟用與觸發 DAGs
所有爬取任務都由 Airflow UI 統一管理。

1.  **訪問 Airflow UI**: 打開 [http://localhost:8080](http://localhost:8080)。
2.  **啟用 DAG**: 在主畫面，您會看到為每個平台建立的 DAGs (例如 `crawler_pipeline_platform_104`)。點擊每個 DAG 左側的 **開關** 將其從 `Paused` 狀態切換為 `Active`。
3.  **手動觸發**: 
    *   點擊 DAG 名稱進入該 DAG 的詳細視圖。
    *   點擊右上角的 "**Trigger DAG**" 按鈕 (▶️ 圖示)。
    *   選擇 "**Trigger**" 來手動運行一次工作流。
4.  **自動排程**: 根據預設，每個 DAG 會在每天的 `03:00` 自動運行。

### 3. 監控執行流程
*   **Airflow UI**: 在 "Grid" 或 "Graph" 視圖中，可以看到任務 (`category`, `urls`, `details`) 的執行狀態、日誌和歷史紀錄。
*   **Flower UI**: 可以看到被 Airflow 觸發的 Celery 任務的即時狀態，以及執行它們的 Worker 節點。
*   **phpMyAdmin**: 可以看到 `job_data` 資料庫中的 `tb_jobs`, `tb_urls` 等資料表隨著爬取流程的進行而填充數據。

---

## 五、 維護與更新

### 1. 更新爬蟲或 Airflow 程式碼
當您修改了 Python 程式碼 (無論是爬蟲邏輯還是 DAG 定義) 後，需要重建映像並重啟對應的服務。

```bash
# 1. 重新建立映像 (包含所有程式碼變更)
docker build -f dockerfile.airflow -t benitorhuang/airflow-crawler:0.0.1 .

# 2. 更新 Airflow 服務 (Swarm 會進行滾動更新)
docker service update --image benitorhuang/airflow-crawler:0.0.1 airflow_stack_airflow-webserver
docker service update --image benitorhuang/airflow-crawler:0.0.1 airflow_stack_airflow-scheduler

# 3. (如果修改了爬蟲 Worker 的程式碼) 更新爬蟲服務
# 注意：此處的 image 應為 crawler_main_stack 使用的 image
# docker service update --image <YOUR_CRAWLER_IMAGE> crawler_main_stack_worker-default
```

### 2. 清理環境

```bash
# 移除 Airflow 堆疊
docker stack rm airflow_stack

# 移除核心爬蟲堆疊
docker stack rm crawler_main_stack

# (可選) 讓節點離開 Swarm 叢集以完全重置
docker swarm leave --force
```