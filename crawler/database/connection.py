# crawler/database/connection.py
"""
此模組負責管理與資料庫的連接。
"""
import logging
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from tenacity import retry, stop_after_attempt, wait_exponential, before_log, RetryError
from crawler.settings import settings
from crawler.database.schema import metadata

logger = logging.getLogger(__name__)
_engine: Optional[Engine] = None

def get_engine() -> Engine:
    """
    獲取 SQLAlchemy 引擎實例，帶有強大的連接重試機制和正確的字元集配置。
    """
    global _engine
    if _engine is None:
        try:
            @retry(
                stop=stop_after_attempt(10),
                wait=wait_exponential(multiplier=1, min=2, max=30),
                before=before_log(logger, logging.INFO),
                reraise=True
            )
            def _connect_with_retry() -> Engine:
                logger.info("正在嘗試創建 MySQL 引擎...")
                db = settings.db
                # [關鍵修正] 在連接字串中明確指定 charset=utf8mb4
                addr = f"mysql+pymysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.database}?charset=utf8mb4"
                
                engine = create_engine(
                    addr,
                    pool_recycle=3600,
                    echo=False,
                    connect_args={'connect_timeout': 10}, # pymysql-specific
                    isolation_level="READ COMMITTED"
                )
                
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    
                logger.info("MySQL 引擎創建成功且連接測試通過。")
                return engine

            _engine = _connect_with_retry()

        except RetryError as e:
            logger.critical(f"資料庫連接在多次重試後失敗。資料庫可能已關閉或無法訪問。錯誤: {e}", exc_info=True)
            raise RuntimeError("資料庫連接在多次重試後失敗。") from e
        except Exception as e:
            logger.critical(f"創建資料庫引擎時發生意外錯誤: {e}", exc_info=True)
            raise RuntimeError("創建資料庫引擎時發生意外錯誤。") from e
            
    return _engine

def initialize_database() -> None:
    """初始化資料庫，創建所有定義的表結構。"""
    logger.info("正在初始化資料庫表...")
    try:
        engine = get_engine()
        # 確保數據庫本身的默認字符集也是 utf8mb4
        with engine.connect() as connection:
            connection.execute(text(f"ALTER DATABASE {settings.db.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
            logger.info(f"資料庫 '{settings.db.database}' 的字符集已確認/修改為 utf8mb4。")
        
        metadata.create_all(engine)
        logger.info("資料庫表初始化檢查完成。")
        
    except Exception as e:
        logger.critical(f"初始化資料庫表失敗: {e}", exc_info=True)
        raise