問題描述：Q-008
Airflow 的 Celery Worker 無法正常啟動，日誌顯示 "Module 'airflow.providers.celery.executors.default_celery' has no attribute 'celery'"。

解決方案：
1.  **Port 衝突解決**：最初部署 Airflow 和 phpMyAdmin 時遇到 Port 衝突，透過調整 `docker_stack.yml` 和 `docker_airflow.yml` 中的 `published` 和 `target` Port 解決。
2.  **日誌目錄權限問題**：Airflow Worker 無法寫入日誌目錄，導致啟動失敗。此問題需手動在主機上執行 `sudo chown -R 50000:50000 ./logs` 解決。
3.  **Python 模組導入問題**：Airflow DAGs 無法找到 `src` 模組。透過調整 `PYTHONPATH` 環境變數 (`/app:/opt/airflow/dags`) 並修正 `crawler_pipeline.py` 中的導入語句 (`from src.dataflow.etl.crawler import (...)`) 解決。
4.  **Airflow Worker 命令過時**：`airflow worker` 命令已過時，應使用 `airflow celery worker`。已在 `docker_airflow.yml` 中更新。
5.  **Celery App 模組路徑問題**：
    *   最初嘗試使用 `airflow.providers.celery.app` 作為 Celery App 模組，但未找到。
    *   經容器內部檢查，發現正確的模組路徑為 `airflow.providers.celery.executors.default_celery`。
    *   更新 `docker_airflow.yml` 中的 `command` 為 `["python", "-m", "celery", "-A", "airflow.providers.celery.executors.default_celery", "worker", "--loglevel=DEBUG"]`。
    *   然而，新的錯誤訊息顯示 "Module 'airflow.providers.celery.executors.default_celery' has no attribute 'celery'"，表明該模組中沒有直接名為 `celery` 的物件。
6.  **當前狀態**：Celery Worker 仍然無法啟動，問題點在於如何正確引用 `airflow.providers.celery.executors.default_celery` 模組中的 Celery 應用程式實例。

問題根源：
Airflow 的 Celery Worker 無法正確啟動，主要原因在於對 `apache-airflow-providers-celery` 內部 Celery 應用程式實例的引用方式不正確。儘管已安裝相關套件並嘗試了多種模組路徑，但仍未能找到正確的 Celery App 物件。

解決方案的有效性：
目前問題尚未完全解決，Celery Worker 仍無法正常啟動。需要進一步研究 `apache-airflow-providers-celery` 內部如何暴露其 Celery 應用程式實例，或考慮其他啟動 Celery Worker 的方式。

---

問題描述：Q-009
在 Airflow UI 中，所有 DAGs 都顯示為 "Broken"，並出現多種導入錯誤，如 `ModuleNotFoundError: No module named 'src'` 和 `ImportError: attempted relative import with no known parent package`。

解決方案：
此問題的根本原因在於 Airflow 環境（Webserver 和 Scheduler 容器）與爬蟲專案的原始碼完全隔離，導致 Python 無法找到 `src` 或 `crawler` 等模組。解決方案是對 Docker 環境的建置和配置流程進行了根本性的修正。

1.  **核心思路轉變**：從「僅複製 DAGs 文件到容器」轉變為「將整個專案作為一個 Python 套件安裝到 Airflow 映像中」。

2.  **`dockerfile.airflow` 重構**：
    *   將整個專案 (`COPY . .`) 複製到映像的一個臨時工作目錄 (`/project`)。
    *   使用 `chown -R airflow:root /project` 修正文件權限問題，確保 `airflow` 用戶有權讀取。
    *   執行 `pip install --user /project`，將專案本身安裝到 `airflow` 用戶的 site-packages 目錄下。這從根本上解決了 `PYTHONPATH` 的問題。

3.  **依賴與環境配置修正**：
    *   **`pyproject.toml`**：修正了兩個與環境不符的依賴問題：
        *   將 `playwright` 的版本要求從不存在的 `>=1.53.0` 修正為 `_1.48.0`。
        *   將 Python 版本要求從 `>=3.11` 降級為 `>=3.8`，以匹配 Airflow 基礎映像的 Python 版本。
    *   **`requirements-airflow.txt`**：為確保完整性，添加了 `apache-airflow-providers-postgres`。
    *   **`docker_airflow.yml`**：
        *   移除了所有服務中已不再需要的 `PYTHONPATH` 環境變數。
        *   將 `AIRFLOW__CORE__DAGS_FOLDER` 的路徑修正為指向專案內部正確的 dags 目錄 (`/opt/airflow/project/src/dataflow/dags`)。

4.  **DAG 導入路徑修正**：
    *   修改 `src/dataflow/dags/crawler_pipeline.py`，將導入語句從 `from etl.crawler import ...` 改為 `from src.dataflow.etl.crawler import ...`，使其與作為已安裝套件的專案結構一致。

5.  **重建與部署**：
    *   在應用上述所有修改後，執行 `docker stack rm airflow_stack` 清理舊環境。
    *   執行 `docker build -f dockerfile.airflow ...` 重建映像。
    *   執行 `docker stack deploy ...` 重新部署。

問題根源：
Airflow 容器的 `PYTHONPATH` 中不包含專案的原始碼目錄，且 Docker 映像的建置過程中存在權限問題、Python 版本不匹配和套件版本不匹配等多重錯誤。

解決方案的有效性：
非常有效。在完成上述所有步驟並重新部署後，Airflow UI 中的所有 DAGs 均已成功加載，不再出現任何導入錯誤，系統恢復正常。
