# crawler/projects/platform_104/parsers.py
"""104平台的數據翻譯官 (Data Translator)。

此模組包含一系列純函數，負責將從 104 API 獲取的原始 JSON 數據
轉換為我們系統內部標準化的資料庫模型（如 Job, CategorySource）。
這些函數不執行任何 I/O 操作或包含業務流程邏輯，僅專注於數據轉換。
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from crawler.database.schema import Job, CategorySource
from crawler.enums import SalaryType, JobType, SourcePlatform, JobStatus
from crawler.utils import clean_text

logger = logging.getLogger(__name__)

def _safe_get(data: Dict, keys: List[str], default: Any = None) -> Any:
    """安全地從嵌套字典中獲取值。"""
    for key in keys:
        if not isinstance(data, dict) or (data := data.get(key)) is None:
            return default
    return data

def transform_categories_to_source_model(raw_data: List[Dict]) -> List[Dict]:
    """將 104 的樹狀分類 API 數據扁平化為資料庫模型列表。"""
    flat_list = []
    def _flatten(nodes: List[Dict], parent_id: Optional[str] = None):
        for node in nodes:
            if source_id := node.get("no"):
                flat_list.append({
                    "source_platform": SourcePlatform.PLATFORM_104,
                    "source_category_id": source_id,
                    "source_category_name": node.get("des"),
                    "parent_source_id": parent_id,
                })
                if "n" in node and node["n"]:
                    _flatten(node["n"], source_id)
    _flatten(raw_data)
    return flat_list

def transform_details_to_job_model(api_data: Dict[str, Any], url: str) -> Optional[Job]:
    """將 104 的職缺詳情 API JSON 數據轉換為標準化的 Job 模型。
    
    Args:
        api_data (Dict[str, Any]): 從 104 內容 API 獲取的 'data' 區塊。
        url (str): 該職缺的原始 URL。

    Returns:
        Optional[Job]: 一個填充了數據的 Job 物件，如果關鍵數據缺失則返回 None。
    """
    try:
        # 契約式斷言：確保核心數據區塊存在
        h = api_data.get('header')
        jd = api_data.get('jobDetail')
        c = api_data.get('condition')
        if not all([h, jd, c, h.get('jobName')]):
            raise ValueError("API 響應中缺少 'header', 'jobDetail', 'condition' 或 'jobName' 等關鍵字段。")

        job_type = {1: JobType.FULL_TIME, 2: JobType.PART_TIME, 3: JobType.CONTRACT}.get(jd.get('jobType'))
        salary_type = {50: SalaryType.MONTHLY, 30: SalaryType.HOURLY}.get(jd.get('salaryType'), SalaryType.NEGOTIABLE)

        posted_at = None
        if appear_date := h.get('appearDate'):
            try:
                posted_at = datetime.strptime(appear_date, "%Y/%m/%d")
            except (ValueError, TypeError):
                logger.warning(f"[104] 無效的日期格式 for {url}: {appear_date}")

        return Job(
            source_platform=SourcePlatform.PLATFORM_104,
            source_job_id=url.split("/")[-1].split("?")[0],
            url=url,
            status=JobStatus.ACTIVE,
            title=h.get('jobName'),
            description=clean_text(jd.get('jobDescription')),
            job_type=job_type,
            location_text=f"{_safe_get(jd, ['addressRegion'], '')}{_safe_get(jd, ['addressDetail'], '')}".strip(),
            posted_at=posted_at,
            salary_text=jd.get('salary'),
            salary_min=jd.get('salaryMin'),
            salary_max=jd.get('salaryMax'),
            salary_type=salary_type,
            experience_required_text=c.get('workExp'),
            education_required_text=c.get('edu'),
            company_source_id=h.get('custNo'),
            company_name=h.get('custName'),
            company_url=h.get('custUrl'),
        )
    except (ValueError, AttributeError, TypeError, KeyError) as e:
        # 此處捕獲 ValueError 是為了記錄我們自己的契約式斷言失敗
        logger.error(f"[104] Parser failed for url {url}: {e}", exc_info=True)
        # 向上拋出異常，讓 Orchestrator 進行標準化處理
        raise