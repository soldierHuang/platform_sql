# crawler/database/schema.py
"""SQLModel schemas for the job crawling database."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Text, TIMESTAMP, BigInteger, Enum as EnumDB, UniqueConstraint

from sqlmodel import Field, SQLModel
from crawler.enums import JobStatus, CrawlStatus, JobType, SalaryType, SourcePlatform

class CategorySource(SQLModel, table=True):
    """(Phase 1) 平台原始職務類別表。"""
    __tablename__ = "tb_category_source"
    id: Optional[int] = Field(default=None, primary_key=True)
    source_platform: SourcePlatform = Field(sa_column=Column(EnumDB(SourcePlatform), nullable=False))
    # [最終修正] 增加欄位長度以容納 Cakeresume 的長 ID
    source_category_id: str = Field(max_length=255)
    source_category_name: str = Field(max_length=255)
    # [最終修正] 增加欄位長度以容納 Cakeresume 的長 ID
    parent_source_id: Optional[str] = Field(default=None, max_length=255)
    __table_args__ = (UniqueConstraint("source_platform", "source_category_id", name="uq_source_category"),)

class Url(SQLModel, table=True):
    """(Phase 1) 職缺 URL 表，追蹤其生命週期。"""
    __tablename__ = "tb_urls"
    source_url: str = Field(primary_key=True, max_length=512)
    source: SourcePlatform = Field(sa_column=Column(EnumDB(SourcePlatform), nullable=False, index=True))
    status: JobStatus = Field(default=JobStatus.ACTIVE, sa_column=Column(EnumDB(JobStatus), nullable=False, index=True))
    details_crawl_status: CrawlStatus = Field(default=CrawlStatus.PENDING, sa_column=Column(EnumDB(CrawlStatus), nullable=False, index=True))
    crawled_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(TIMESTAMP, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(TIMESTAMP, nullable=False, onupdate=datetime.utcnow))
    details_crawled_at: Optional[datetime] = Field(default=None, sa_column=Column(TIMESTAMP))

class Job(SQLModel, table=True):
    """(Phase 1) 標準化職缺詳情表。"""
    __tablename__ = "tb_jobs"
    id: Optional[int] = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    source_platform: SourcePlatform = Field(sa_column=Column(EnumDB(SourcePlatform), nullable=False, index=True))
    # [最終修正] 確保 source_job_id 長度足以容納各種平台 ID
    source_job_id: str = Field(max_length=255, index=True)
    url: str = Field(max_length=512, index=True)
    status: JobStatus = Field(sa_column=Column(EnumDB(JobStatus), nullable=False))
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    job_type: Optional[JobType] = Field(default=None, sa_column=Column(EnumDB(JobType)))
    location_text: Optional[str] = Field(default=None, max_length=255)
    posted_at: Optional[datetime] = Field(default=None)
    salary_text: Optional[str] = Field(default=None, max_length=255)
    salary_min: Optional[int] = Field(default=None)
    salary_max: Optional[int] = Field(default=None)
    salary_type: Optional[SalaryType] = Field(default=None, sa_column=Column(EnumDB(SalaryType)))
    # [最終修正] 增加長度
    experience_required_text: Optional[str] = Field(default=None, max_length=255)
    # [最終修正] 增加長度
    education_required_text: Optional[str] = Field(default=None, max_length=255)
    # [最終修正] 增加長度
    company_source_id: Optional[str] = Field(default=None, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    company_url: Optional[str] = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(TIMESTAMP, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(TIMESTAMP, nullable=False, onupdate=datetime.utcnow))
    __table_args__ = (UniqueConstraint("source_platform", "source_job_id", name="uq_source_job"),)

metadata = SQLModel.metadata