#  針對 platform_104, platform_1111, 和 platform_cakeresume 的數據採集平台測試指令

# <<< 第一部分 : 本地部屬 >>>
## 使用 Docker Compose 來部署和管理服務
docker compose up --build -d
# docker compose down -v # 停止並移除容器及卷

# 查看服務狀態
docker compose ps 
# 確保 app, worker-default, worker-category, mysql, redis 服務都處於 running/healthy 狀態

## 驗證服務與訪問管理工具
- API (FastAPI)	查看 API 文檔和進行交互式測試
http://localhost:8000/docs	

- Flower	監控 Celery Worker 和任務狀態
http://localhost:5555

- RabbitMQ Mgmt	查看消息隊列的詳細狀態
http://localhost:15672	guest	guest	

- phpMyAdmin	管理 job_data 資料庫
http://localhost:8080	root	root_password	

- Portainer	圖形化管理 Docker 容器和服務
http://localhost:9000	(首次需設定)	(首次需設定)


# 資料庫初始化
docker compose exec app crawler db init
# 查看資料庫狀況 (範例)
# docker compose exec mysql bash
# mysql -uuser -ppassword job_data
# SELECT * FROM tb_category_source LIMIT 1\G
# SELECT * FROM tb_urls LIMIT 1\G
# SELECT * FROM tb_jobs LIMIT 1\G
# SELECT source, details_crawl_status, source_url FROM tb_urls ORDER BY crawled_at DESC LIMIT 5;
# docker compose exec mysql mysql -uuser -ppassword job_data -e "SELECT COUNT(*) FROM tb_urls WHERE source = 'platform_104';"


### platform_104 功能測試 ( 職業分類 / 網址 / 頁面資料 )
docker compose exec app celery -A crawler.app call platform_104.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_104 --category-id 2007001001
docker compose exec app python -m crawler.cli task details platform_104 --limit 5

### platform_1111 功能測試 ( 職業分類 / 網址 / 頁面資料 )
docker compose exec app celery -A crawler.app call platform_1111.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_1111 --category-id 140100
docker compose exec app python -m crawler.cli task details platform_1111 --limit 5

### platform_yes123 功能測試  ( 職業分類 / 網址 / 頁面資料 )
docker compose exec app celery -A crawler.app call platform_yes123.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_yes123 --category-id '2_1001_0001_0003'
docker compose exec app python -m crawler.cli task details platform_yes123 --limit 5

### platform_cakeresume 功能測試  ( 職業分類 / 網址 / 頁面資料 )
docker compose exec worker-category celery -A crawler.app call platform_cakeresume.run_category_pipeline
docker compose exec app python -m crawler.cli task urls platform_cakeresume --category-id 'it_software-engineer'
docker compose exec app python -m crawler.cli task details platform_cakeresume --limit 5



<!-- # 操作過程重啟服務 (可選但建議): 為了確保 Celery worker 加載最新的程式碼，可以重啟一下服務。
docker compose restart worker-category
docker logs worker-category -->
<!-- docker volume rm $(docker volume ls -q) -->
<!-- docker rmi $(docker images -f "dangling=true" -q) -->



# <<< 第二部分 : 使用 Docker Compose 來部署和管理服務 >>>

# 建立 docker image
docker build -f Dockerfile -t benitorhuang/platform_sql:0.0.1 .

# 使用 Docker Compose 來部署和管理服務
docker compose -f plantform_sql.yml up -d

# 初始化資料庫
docker compose -f plantform_sql.yml exec app python -m crawler.cli db init

# 查看服務狀態
docker compose -f plantform_sql.yml ps

- http://localhost:8000/docs	 # FastAPI API 文檔
- http://localhost:5555	         # Flower 監控 Celery Worker
- http://localhost:15672	     # RabbitMQ 管理界面 (guest/guest)
- http://localhost:8080	         # phpMyAdmin 管理界面 (root/root_password)

<!-- # 查看資料庫狀況
docker compose -f plantform_sql.yml exec mysql bash mysql -uuser -ppassword job_data
# 查看資料表內容
SELECT * FROM tb_category_source LIMIT 1\G
SELECT * FROM tb_urls LIMIT 1\G
SELECT * FROM tb_jobs LIMIT 1\G
SELECT source, details_crawl_status, source_url FROM tb_urls ORDER BY crawled_at DESC LIMIT 5; -->


# <<< 第三部分 : 使用 Docker 執行 Platform 平台功能 >>>
# 針對 platform_104 功能指令
docker compose -f plantform_sql.yml exec app celery -A crawler.app call platform_104.run_category_pipeline
docker compose -f plantform_sql.yml exec app python -m crawler.cli task urls platform_104 --category-id 2007001001
docker compose -f plantform_sql.yml exec app python -m crawler.cli task details platform_104 --limit 5

# 針對 platform_1111 功能指令
docker compose -f plantform_sql.yml exec app celery -A crawler.app call platform_1111.run_category_pipeline
docker compose -f plantform_sql.yml exec app python -m crawler.cli task urls platform_1111 --category-id 140100
docker compose -f plantform_sql.yml exec app python -m crawler.cli task details platform_1111 --limit 5

# 針對 platform_yes123 功能指令
docker compose -f plantform_sql.yml exec app celery -A crawler.app call platform_yes123.run_category_pipeline
docker compose -f plantform_sql.yml exec app python -m crawler.cli task urls platform_yes123 --category-id '2_1001_0001_0003'
docker compose -f plantform_sql.yml exec app python -m crawler.cli task details platform_yes123 --limit 5

# 針對 platform_cakeresume 功能指令
docker compose -f plantform_sql.yml exec worker-category celery -A crawler.app call platform_cakeresume.run_category_pipeline
docker compose -f plantform_sql.yml exec app python -m crawler.cli task urls platform_cakeresume --category-id 'it_software-engineer'
docker compose -f plantform_sql.yml exec app python -m crawler.cli task details platform_cakeresume --limit 5





# 使用 airflow 來管理和監控任務
# docker compose up --build -d
# airflow dags test Crawler_104_Sharded 2024-01-01