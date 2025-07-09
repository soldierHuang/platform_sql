# crawler/database/repository.py
"""Database repository for interacting with the job crawling data."""
import logging
from datetime import datetime
from typing import List, Dict, Set, Optional, Any

from sqlalchemy import update
from sqlalchemy.dialects.mysql import insert
import sqlalchemy.sql as sql
from sqlmodel import Session, select

from crawler.database.connection import get_engine
from crawler.database.schema import Url, Job, CategorySource
from crawler.enums import SourcePlatform, CrawlStatus, JobStatus

logger = logging.getLogger(__name__)

def sync_source_categories(platform: SourcePlatform, flattened_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    # ... (此函數不變)
    if not flattened_data:
        return {"total": 0, "affected": 0}
    
    with Session(get_engine()) as session:
        stmt = insert(CategorySource).values(flattened_data)
        update_dict = {
            "source_category_name": stmt.inserted.source_category_name,
            "parent_source_id": stmt.inserted.parent_source_id,
        }
        stmt = stmt.on_duplicate_key_update(**update_dict)
        result = session.execute(stmt)
        session.commit()
        logger.info(f"[{platform.value}] Synced {result.rowcount} categories (out of {len(flattened_data)} total).")
        return {"total": len(flattened_data), "affected": result.rowcount}

def get_source_categories(platform: SourcePlatform, source_ids: Optional[List[str]] = None) -> List[CategorySource]:
    # ... (此函數不變)
    with Session(get_engine()) as session:
        stmt = select(CategorySource).where(CategorySource.source_platform == platform)
        if source_ids:
            stmt = stmt.where(CategorySource.source_category_id.in_(source_ids))
        return session.exec(stmt).all()

def upsert_urls(platform: SourcePlatform, urls: List[str]) -> None:
    """
    Synchronizes a list of URLs for a given platform with the database.
    Performs an UPSERT operation. URLs are marked as ACTIVE and PENDING.
    """
    if not urls:
        return

    now = datetime.utcnow()
    # [關鍵修正] 這裡 urls 參數現在明確是 List[str]
    url_models_to_upsert = [
        {
            "source_url": u,
            "source": platform,
            "status": JobStatus.ACTIVE,
            "details_crawl_status": CrawlStatus.PENDING,
            "crawled_at": now,
            "updated_at": now,
        }
        for u in urls
    ]

    with Session(get_engine()) as session:
        stmt = insert(Url).values(url_models_to_upsert)
        update_dict = {
            "status": stmt.inserted.status,
            "updated_at": stmt.inserted.updated_at,
            "details_crawl_status": stmt.inserted.details_crawl_status,
        }
        stmt = stmt.on_duplicate_key_update(**update_dict)
        session.execute(stmt)
        session.commit()

def get_unprocessed_urls(platform: SourcePlatform, limit: int) -> List[Url]:
    # ... (此函數不變)
    with Session(get_engine()) as session:
        return session.exec(
            select(Url).where(
                Url.source == platform,
                Url.details_crawl_status == CrawlStatus.PENDING
            ).limit(limit)
        ).all()

def upsert_jobs(jobs: List[Job]) -> None:
    # ... (此函數不變)
    if not jobs:
        return
        
    with Session(get_engine()) as session:
        try:
            now = datetime.utcnow()
            job_dicts_to_upsert = []
            for job in jobs:
                job_dict = job.model_dump(exclude_none=False)
                job_dict['updated_at'] = now
                if 'created_at' not in job_dict:
                    job_dict['created_at'] = now
                job_dicts_to_upsert.append(job_dict)

            if not job_dicts_to_upsert:
                return

            stmt = insert(Job).values(job_dicts_to_upsert)
            
            update_cols = {
                "source_platform": stmt.inserted.source_platform,
                "source_job_id": stmt.inserted.source_job_id,
                "url": stmt.inserted.url,
                "status": stmt.inserted.status,
                "title": stmt.inserted.title,
                "description": stmt.inserted.description,
                "job_type": stmt.inserted.job_type,
                "location_text": stmt.inserted.location_text,
                "posted_at": stmt.inserted.posted_at,
                "salary_text": stmt.inserted.salary_text,
                "salary_min": stmt.inserted.salary_min,
                "salary_max": stmt.inserted.salary_max,
                "salary_type": stmt.inserted.salary_type,
                "experience_required_text": stmt.inserted.experience_required_text,
                "education_required_text": stmt.inserted.education_required_text,
                "company_source_id": stmt.inserted.company_source_id,
                "company_name": stmt.inserted.company_name,
                "company_url": stmt.inserted.company_url,
                "updated_at": stmt.inserted.updated_at,
            }
            
            final_stmt = stmt.on_duplicate_key_update(**update_cols)
            result = session.execute(final_stmt)
            session.commit()
            logger.info(f"Upserted or updated {result.rowcount} jobs.")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to upsert jobs: {e}", exc_info=True)
            raise

def mark_urls_as_crawled(processed_urls: Dict[CrawlStatus, List[str]]) -> None:
    # ... (此函數不變)
    now = datetime.utcnow()
    with Session(get_engine()) as session:
        for status, urls in processed_urls.items():
            if urls:
                stmt = update(Url).where(Url.source_url.in_(urls)).values(
                    details_crawl_status=status,
                    details_crawled_at=now
                )
                session.execute(stmt)
        session.commit()