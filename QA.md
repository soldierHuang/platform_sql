問題描述：<問題 Q-001> 嘗試在 `run_shell_command` 中設置並使用環境變數時，命令被拒絕。
解決方案：<解決方案> `run_shell_command` 不支持在單一命令中設置環境變數並立即使用。需要將操作拆分為兩個獨立的步驟：首先獲取容器 ID，然後在後續命令中使用該 ID。

問題描述：<問題 Q-002> Airflow 在載入 DAG 時，無法從 `src.dataflow.etl.crawler` 導入 `SourcePlatform`。
解決方案：<解決方案> 檢查 `src/dataflow/etl/crawler.py` 文件，確認 `SourcePlatform` 是否有被定義。同時，由於 `dockerfile.airflow` 將 `src/dataflow` 複製到 `/opt/airflow/dags/`，因此在 `crawler_pipeline.py` 中，導入路徑應該是 `from etl.crawler import ...` 而不是 `from src.dataflow.etl.crawler import ...`。

問題描述：<問題 Q-003> 儘管修改了 `crawler_pipeline.py` 中的導入路徑為 `from etl.crawler import`，但仍然出現 `ModuleNotFoundError: No module named 'etl'`。
解決方案：<解決方案> 這個錯誤表明 Python 在 Airflow 容器的環境中無法找到 `etl` 模組。這可能是由於 `PYTHONPATH` 沒有正確生效，或者 `etl` 目錄沒有被 Python 識別為一個包。

問題描述：<問題 Q-004> 儘管已經創建了 `__init__.py` 文件並恢復了導入路徑，但 `airflow db migrate` 仍然報告 `ImportError: cannot import name 'SourcePlatform' from 'src.dataflow.etl.crawler'`。
解決方案：<解決方案> 這個錯誤表明 Airflow 在嘗試載入 DAG 文件時，仍然無法正確解析 `src.dataflow.etl.crawler` 模組。這可能是因為 `PYTHONPATH` 的設置沒有完全生效，或者 Airflow 的 DAG 載入機制沒有正確地將 `src` 目錄添加到 Python 的模組搜索路徑中。

問題描述：<問題 Q-005> `src/dataflow/etl/crawler.py` 中缺少 `SourcePlatform` 的定義，導致 `ImportError`。
解決方案：<解決方案> 在 `src/dataflow/etl/crawler.py` 中導入 `SourcePlatform`。

問題描述：<問題 Q-006> 在 `src/dataflow/etl/crawler.py` 中嘗試導入 `crawler.enums` 時，出現 `ModuleNotFoundError: No module named 'crawler'`。
解決方案：<解決方案> 這個錯誤表明 Python 無法找到 `crawler` 模組。儘管 `PYTHONPATH` 設置為 `/opt/airflow/project`，但 `crawler` 模組位於 `/opt/airflow/project/crawler`。這意味著 `crawler` 模組本身沒有被正確識別為一個頂級包。

問題描述：<問題 Q-007> 儘管已採取多項措施（包括確保 `__init__.py` 文件存在、設置 `PYTHONPATH`、複製整個項目），`airflow db migrate` 仍然報告 `ModuleNotFoundError: No module named 'crawler'`。
解決方案：<解決方案> 這個錯誤表明 Airflow 在容器內仍然無法找到 `crawler` 模組。這可能是由於文件複製或 `PYTHONPATH` 設置的細微問題。我將再次確認容器內的文件結構，特別是 `crawler` 目錄的位置和內容。

問題描述：<問題 Q-008> `replace` 工具失敗，因為 `old_string` 在 `docker_airflow.yml` 中出現了多次。
解決方案：<解決方案> 我需要對 `docker_airflow.yml` 中的 `airflow-webserver` 和 `airflow-scheduler` 服務分別執行 `replace` 操作。

問題描述：<問題 Q-009> 重新構建 Airflow Docker 映像時，出現 `ERROR: Could not open requirements file: [Errno 2] No such file or directory: '/opt/airflow/project/requirements-airflow.txt'`。
解決方案：<解決方案> 這個錯誤是因為 `dockerfile.airflow` 中的 `COPY . /opt/airflow/` 命令將整個項目複製到 `/opt/airflow/`，所以 `requirements-airflow.txt` 應該在 `/opt/airflow/requirements-airflow.txt`，而不是 `/opt/airflow/project/requirements-airflow.txt`。

問題描述：<問題 Q-010> 嘗試執行 `airflow db migrate` 時，容器 `94642a474baa` 沒有運行。
解決方案：<解決方案> 這表示 Airflow Webserver 容器在重新部署後沒有成功啟動。這可能是由於配置錯誤或依賴問題。

問題描述：<問題 Q-011> 創建 Airflow 管理員帳號時，提示 `admin already exist in the db`。
解決方案：<解決方案> 這表示 `admin` 用戶已經存在於資料庫中。這不是一個錯誤，只是提示用戶已存在。