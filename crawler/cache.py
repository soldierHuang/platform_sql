# crawler/cache.py
"""Redis 客戶端管理器 (Redis Client Manager)。

此模組負責以單例模式（Singleton Pattern）創建和管理 Redis 連接。
確保整個應用程式在多線程環境下共享同一個高效的連接池，避免
重複創建連接的開銷。
"""
import logging
import redis
from typing import Optional  # [關鍵修正] 新增導入 Optional
from redis.client import Redis as RedisClient
from crawler.settings import settings

logger = logging.getLogger(__name__)
_redis_client: Optional[RedisClient] = None

def get_redis_client() -> RedisClient:
    """獲取一個全域共享的 Redis 客戶端實例。

    如果客戶端尚未初始化，此函數將根據 `settings.py` 中的配置創建
    一個新的連接池和客戶端。後續所有調用都將返回同一個客戶端實例。

    Returns:
        RedisClient: 已連接並可用的 Redis 客戶端。

    Raises:
        RuntimeError: 如果無法連接到 Redis 服務器。
    """
    global _redis_client
    if _redis_client is None:
        try:
            rs = settings.redis
            logger.info(f"正在初始化 Redis 客戶端，目標: {rs.host}:{rs.port}")
            pool = redis.ConnectionPool(host=rs.host, port=rs.port, db=rs.db, decode_responses=True)
            _redis_client = RedisClient(connection_pool=pool)
            _redis_client.ping()
            logger.info("Redis 客戶端連接成功。")
        except redis.exceptions.RedisError as e:
            logger.critical(f"Redis 連接失敗: {e}", exc_info=True)
            raise RuntimeError("無法初始化 Redis 連接。") from e
    return _redis_client