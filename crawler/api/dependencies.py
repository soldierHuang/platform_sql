# crawler/api/dependencies.py
"""API 依賴注入器 (API Dependency Injector)。

此模組利用 FastAPI 強大的依賴注入系統，為 API 端點提供必要的
共享資源，最典型的例子就是資料庫會話 (`Session`)。

通過定義 `get_db_session` 生成器，我們可以確保每個請求都獲得
一個獨立的資料庫會話，並在請求結束後自動關閉，從而實現了
資源的有效管理和線程安全。
"""
from typing import Generator, Annotated
from fastapi import Depends
from sqlmodel import Session

from crawler.database.connection import get_engine

def get_db_session() -> Generator[Session, None, None]:
    """為 API 端點提供一個資料庫會話的依賴。"""
    with Session(get_engine()) as session:
        yield session

# 創建一個 Annotated 類型別名，使在 API 端點中引用依賴更簡潔
DBSession = Annotated[Session, Depends(get_db_session)]