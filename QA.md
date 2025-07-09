問題描述：Q-006
重新測試所有平台，確保之前的所有修正都已生效，並且數據能夠正確地從各平台抓取、解析並存儲到資料庫中。

解決方案：
1. **環境清理：** 執行 `docker compose down -v` 停止並移除所有 Docker 容器及相關的數據卷，確保資料庫是全新的狀態。
2. **環境啟動：** 執行 `docker compose up --build -d` 重新啟動所有 Docker 服務。
3. **資料庫初始化：** 執行 `docker compose exec app python -m crawler.cli db init` 初始化資料庫，創建所有必要的表結構。
4. **逐一測試各平台：**
   - **platform_104：**
     - `docker compose exec app celery -A crawler.app call platform_104.run_category_pipeline`
     - `docker compose exec app python -m crawler.cli task urls platform_104 --category-id 2007001001`
     - `docker compose exec app python -m crawler.cli task details platform_104 --limit 5`
     - **驗證：** 查詢 `tb_jobs` 表，確認 `platform_104` 的職缺數據（包括薪資、發布時間、地點等）已正確存儲。
   - **platform_1111：**
     - `docker compose exec app celery -A crawler.app call platform_1111.run_category_pipeline`
     - `docker compose exec app python -m crawler.cli task urls platform_1111 --category-id 140100`
     - `docker compose exec app python -m crawler.cli task details platform_1111 --limit 5`
     - **驗證：** 查詢 `tb_jobs` 表，確認 `platform_1111` 的職缺數據（特別是薪資解析，如「X萬元」的轉換）已正確存儲。
   - **platform_yes123：**
     - `docker compose exec app celery -A crawler.app call platform_yes123.run_category_pipeline`
     - `docker compose exec app python -m crawler.cli task urls platform_yes123 --category-id '2_1001_0001_0003'`
     - `docker compose exec app python -m crawler.cli task details platform_yes123 --limit 5`
     - **驗證：** 查詢 `tb_jobs` 表，確認 `platform_yes123` 的職缺數據已正確存儲。
   - **platform_cakeresume：**
     - `docker compose exec worker-category celery -A crawler.app call platform_cakeresume.run_category_pipeline`
     - `docker compose exec app python -m crawler.cli task urls platform_cakeresume --category-id 'it_software-engineer'`
     - `docker compose exec app python -m crawler.cli task details platform_cakeresume --limit 5`
     - **驗證：** 查詢 `tb_jobs` 表，確認 `platform_cakeresume` 的職缺數據（特別是公司名稱、公司 URL、描述、發布時間、地點等）已正確存儲。

問題根源：
無特定問題根源，此為全面性回歸測試，旨在驗證之前所有問題的修正效果。

解決方案的有效性：
所有平台在經過完整的抓取、解析和存儲流程後，數據均能正確地寫入 `tb_jobs` 表，證明之前針對各平台解析問題的修正均已生效。這也驗證了整個爬蟲框架的穩定性和數據處理的正確性。