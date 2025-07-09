
# 啟動 docker_stack 確認 [docker swarm](./v2_docker_to_swarm.md) 正常運行 
docker stack deploy -c docker_stack.yml crawler_main_stack
docker stack ps crawler_main_stack

# 創建共享網絡 Docker Overlay Network
docker network create --driver overlay --attachable crawler_net


# 啟動 Airflow 服務
<!-- # 創建 Airflow 元數據庫所需的目錄 
mkdir -p ./logs ./plugins -->

## Airflow 需要初始化它自己的元數據資料庫，並創建一個管理員用戶
# 部署 Airflow Stack
docker stack deploy -c docker_airflow.yml airflow_stack

## 初始化 Airflow 資料庫和用戶
# 找到 airflow-webserver 服務的一個容器 ID
AIRFLOW_CONTAINER_ID=$(docker ps --filter "name=airflow_stack_airflow-webserver" --format "{{.ID}}" | head -n 1)

# 在容器內執行資料庫遷移
docker exec $AIRFLOW_CONTAINER_ID airflow db migrate

# 在容器內創建管理員用戶 (用戶名: admin, 密碼: admin)
docker exec $AIRFLOW_CONTAINER_ID airflow users create \
    --username admin \
    --firstname Airflow \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    -p admin


# 驗證 Airflow 與全自動化
- 訪問 Airflow UI   http://localhost:8080 (admin / admin) 
- 檢查 DAGs
- 啟用並觸發 DAG 等待排程時間到達（schedule="0 3 * * *"，即每天凌晨 3 點）
- 監控執行流程
Airflow UI: 在 DAG 的 "Grid" 或 "Graph" 視圖中，你可以看到任務（platform_104_category, platform_104_urls, platform_104_details）的執行狀態。
Flower UI (:5555): 你會看到新的任務被 Airflow 觸發後出現在任務列表中，並由 worker-default 或 worker-category 執行。
phpMyAdmin (:8080): 你會看到資料庫中的數據持續增長。
Portainer (:9000): 你可以查看各個服務的日誌，例如 worker-default 的日誌，來調試爬取過程中的詳細輸出。