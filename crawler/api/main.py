# crawler/api/main.py
"""數據查詢 API (Data Query API)。

此模組使用 FastAPI 構建了一個 Web API 服務，作為數據應用的主要入口。
它提供了多個端點 (endpoints)，允許前端應用或其他後端服務查詢和過濾
已經被爬蟲系統收集並標準化後的職缺數據。
"""
from fastapi import FastAPI, Query, HTTPException
from sqlmodel import select, func
from typing import List, Optional, Dict, Any

from crawler.api.dependencies import DBSession
from crawler.database.schema import Job, Url
from crawler.enums import SourcePlatform, CrawlStatus

app = FastAPI(
    title="多平台職缺數據 API",
    version="2.0.0",
    description="用於訪問由多平台爬蟲收集的職缺數據的 API。",
)

@app.get("/", tags=["通用"], summary="API 根節點")
def read_root():
    """返回一個歡迎信息，可用於健康檢查。"""
    return {"message": "歡迎使用多平台職缺數據 API！"}

@app.get("/jobs/", response_model=List[Job], tags=["職缺數據"], summary="獲取職缺列表")
def get_jobs(
    session: DBSession,
    q: Optional[str] = Query(None, description="對職缺標題或公司名稱進行關鍵字搜索。"),
    platform: Optional[SourcePlatform] = Query(None, description="依平台來源進行過濾。"),
    skip: int = Query(0, ge=0, description="跳過的紀錄數量，用於分頁。"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大紀錄數量。"),
) -> List[Job]:
    """
    從資料庫中檢索一個經過分頁、過濾和排序的職缺列表。
    """
    stmt = select(Job)
    
    if q:
        # 使用 OR 條件進行多字段搜索
        stmt = stmt.where(Job.title.contains(q) | Job.company_name.contains(q))
    
    if platform:
        stmt = stmt.where(Job.source_platform == platform)

    return session.exec(
        stmt.offset(skip).limit(limit).order_by(Job.updated_at.desc())
    ).all()

@app.get("/jobs/{job_id}", response_model=Job, tags=["職缺數據"], summary="獲取單一職缺詳情")
def get_job_by_id(session: DBSession, job_id: int) -> Job:
    """根據資料庫中的主鍵 ID 獲取單一職缺的詳細信息。"""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="找不到指定的職缺 ID。")
    return job

@app.get("/status/summary", tags=["系統狀態"], summary="獲取 URL 狀態統計")
def get_url_status_summary(session: DBSession) -> List[Dict[str, Any]]:
    """
    提供按平台和抓取狀態分組的 URL 計數。
    此端點對於監控爬蟲系統的整體健康狀況和進度非常有用。
    """
    stmt = (
        select(
            Url.source,
            Url.details_crawl_status,
            func.count(Url.source_url).label('count')
        )
        .group_by(Url.source, Url.details_crawl_status)
        .order_by(Url.source, Url.details_crawl_status)
    )
    
    results = session.exec(stmt).all()
    
    return [
        {
            "platform": row.source.value,
            "status": row.details_crawl_status.value,
            "count": row.count
        } for row in results
    ]