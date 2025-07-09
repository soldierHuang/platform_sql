# Docker Swarm 部署與維護指南

本文件旨在引導使用者如何在 Docker Swarm 環境中，從零開始部署、測試及維護本爬蟲應用程式。

---

## 一、 環境初始化與部署

此章節涵蓋首次設定 Docker Swarm 及部署應用程式堆疊的步驟。

### 1. 初始化 Swarm 叢集
首先，需要將您的 Docker 環境初始化為 Swarm 模式。

```bash
# 建議初次或在單一網路介面的環境下使用，讓 Docker 自動偵測 IP
docker swarm init
```
> **備註：** 如果您的主機擁有多個網路介面 (例如同時有實體網卡和虛擬網卡)，Docker 可能會無法決定要使用哪個 IP 作為廣播位址，此時會出現錯誤提示。請依照提示，使用以下指令並明確指定 IP：
> `docker swarm init --advertise-addr <您的主機IP>`

### 2. 部署應用程式堆疊 (Stack)
初始化成功後，使用 `docker_stack.yml` 部署所有服務。

```bash
docker stack deploy -c docker_stack.yml crawler_main_stack
```

### 3. 確認部署狀態
部署後，可使用以下指令檢查服務是否正常運行。

```bash
# 查看目前運行的 stack 列表
docker stack ls

# 查看 stack 中所有服務的狀態 (副本數是否正確、是否正常啟動)
docker service ls

# 查看 Swarm 叢集中的節點資訊
docker node ls
```

---

## 二、 平台功能完整測試

部署完成後，執行以下指令以驗證各平台爬蟲的完整流程 (分類 -> 網址 -> 詳細資料)。

### 1. 獲取 App 服務的容器 ID
為了方便執行指令，先找到 `app` 服務運行的容器 ID。

```bash
# 查找名為 crawler_main_stack_app 的容器並只輸出其 ID
docker ps -f "name=crawler_main_stack_app" -q --no-trunc | head -n 1
```
> **說明：** 請將查詢到的 ID 複製下來，並在後續指令中替換掉 `<APP_CONTAINER_ID>` 的部分。

### 2. 執行資料庫初始化
此指令會在資料庫中創建所有必要的資料表。**每次清空資料庫後都需要重新執行。**

```bash
docker exec <APP_CONTAINER_ID> python -m crawler.cli db init
```

### 3. 逐一測試各平台功能
以下指令將模擬一次完整的爬取流程。

#### Platform 104
```bash
docker exec <APP_CONTAINER_ID> celery -A crawler.app call platform_104.run_category_pipeline
docker exec <APP_CONTAINER_ID> python -m crawler.cli task urls platform_104 --category-id 2007001001
docker exec <APP_CONTAINER_ID> python -m crawler.cli task details platform_104 --limit 5
```

#### Platform 1111
```bash
docker exec <APP_CONTAINER_ID> celery -A crawler.app call platform_1111.run_category_pipeline
docker exec <APP_CONTAINER_ID> python -m crawler.cli task urls platform_1111 --category-id 140100
docker exec <APP_CONTAINER_ID> python -m crawler.cli task details platform_1111 --limit 5
```

#### Platform Yes123
```bash
docker exec <APP_CONTAINER_ID> celery -A crawler.app call platform_yes123.run_category_pipeline
docker exec <APP_CONTAINER_ID> python -m crawler.cli task urls platform_yes123 --category-id '2_1001_0001_0003'
docker exec <APP_CONTAINER_ID> python -m crawler.cli task details platform_yes123 --limit 5
```

#### Platform Cakeresume
```bash
docker exec <APP_CONTAINER_ID> celery -A crawler.app call platform_cakeresume.run_category_pipeline
docker exec <APP_CONTAINER_ID> python -m crawler.cli task urls platform_cakeresume --category-id 'it_software-engineer'
docker exec <APP_CONTAINER_ID> python -m crawler.cli task details platform_cakeresume --limit 5
```

---

## 三、 日常維護與偵錯

此章節提供解決常見問題的指令。

### 1. Docker 服務本身的問題
當所有 `docker` 指令都無法執行時，優先檢查 Docker 服務本身。

```bash
# 查看 Docker 服務的詳細狀態 (是否 active/running)
systemctl status docker.service

# 嘗試重新啟動 Docker 服務
sudo systemctl restart docker.service
```
> **進階偵錯：** 如果 Docker 服務啟動失敗 (`failed`)，通常是設定檔 `/etc/docker/daemon.json` 損毀。可透過以下指令將其備份，讓 Docker 使用預設值重啟，這能解決大部分啟動問題。
> `sudo mv /etc/docker/daemon.json /etc/docker/daemon.json.bak`

### 2. 網路連線問題
如果服務已啟動，但瀏覽器無法訪問，請檢查網路和防火牆。

```bash
# 查看防火牆狀態 (確認端口是否被阻擋)
sudo ufw status

# 檢查特定端口 (例如 5555) 是否正在被監聽
# ss 是比 netstat 更現代的工具
sudo ss -tulpn | grep 5555
```
> `ss` 指令參數解說：
> - `-t`: 顯示 TCP sockets
> - `-u`: 顯示 UDP sockets
> - `-l`: 只顯示監聽中的 sockets
> - `-p`: 顯示使用該 socket 的進程
> - `-n`: 以數字形式顯示端口號

### 3. Swarm 環境管理
管理 Swarm 叢集和部署的服務。

```bash
# 徹底移除已部署的 stack (包含所有服務、網路)
docker stack rm crawler_main_stack

# 讓當前節點離開 Swarm 叢集 (用於重置 Swarm 環境)
docker swarm leave --force
```