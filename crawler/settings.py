# crawler/settings.py
"""統一配置管理中心 (The Rulebook)。

此模組使用 Pydantic V2 進行配置管理，提供了類型安全、環境變數載入
和預設值設定等強大功能。所有基礎設施（資料庫、Redis、RabbitMQ）
和特定平台（104, 1111等）的配置都集中在此，是系統的唯一真實來源 (SSOT)。
"""
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict

# --- 平台特定配置模型 ---

class Project104Settings(BaseModel):
    """104 平台的特定配置。"""
    max_pages: int = 3
    max_workers: int = 5
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.104.com.tw/jobs/search/",
    }

class Project1111Settings(BaseModel):
    """1111 平台的特定配置。"""
    max_pages: int = 3
    max_workers: int = 5
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.1111.com.tw/",
    }

class ProjectCakeresumeSettings(BaseModel):
    """Cakeresume 平台的特定配置。"""
    max_pages: int = 2
    max_workers: int = 5
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.cakeresume.com/jobs",
    }

class ProjectYes123Settings(BaseModel):
    """Yes123 平台的特定配置。"""
    max_pages: int = 5
    max_workers: int = 5
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.yes123.com.tw/",
    }

# --- 基礎設施配置模型 ---

class DatabaseSettings(BaseSettings):
    """資料庫連接配置。"""
    host: str = "mysql"
    port: int = 3306
    user: str = "user"
    password: str = "password"
    database: str = "job_data"
    model_config = SettingsConfigDict(env_prefix='MYSQL_')

class RabbitMQSettings(BaseSettings):
    """RabbitMQ (Celery Broker) 連接配置。"""
    host: str = "rabbitmq"
    port: int = 5672
    default_user: str = "guest"
    default_pass: str = "guest"
    model_config = SettingsConfigDict(env_prefix='RABBITMQ_')

class RedisSettings(BaseSettings):
    """Redis (Celery Backend & Cache) 連接配置。"""
    host: str = "redis"
    port: int = 6379
    db: int = 0
    model_config = SettingsConfigDict(env_prefix='REDIS_')

# --- 主配置類 ---

class Settings(BaseSettings):
    """主配置類，聚合所有配置項。"""
    db: DatabaseSettings = DatabaseSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    redis: RedisSettings = RedisSettings()
    
    # 聚合所有平台配置
    p104: Project104Settings = Project104Settings()
    p1111: Project1111Settings = Project1111Settings()
    pcake: ProjectCakeresumeSettings = ProjectCakeresumeSettings()
    pyes123: ProjectYes123Settings = ProjectYes123Settings()
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_nested_delimiter='__', extra='ignore')

# --- 創建全域唯一的配置實例 ---
settings = Settings()

# --- 組建 Broker URL for Celery ---
celery_broker_url = f"pyamqp://{settings.rabbitmq.default_user}:{settings.rabbitmq.default_pass}@{settings.rabbitmq.host}:{settings.rabbitmq.port}/"
celery_result_backend = f"redis://{settings.redis.host}:{settings.redis.port}/{settings.redis.db}"