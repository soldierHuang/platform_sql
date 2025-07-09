# crawler/projects/platform_cakeresume/parsers.py
"""
Parsers for Cakeresume, handling data transformation from various sources
like APIs and HTML content.
"""
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
import re # Ensure re is imported for regex
from bs4 import BeautifulSoup # Import BeautifulSoup

from crawler.database.schema import Job
from crawler.enums import SourcePlatform, JobStatus, SalaryType, JobType
from crawler.utils import clean_text

logger = logging.getLogger(__name__)

def _parse_cakeresume_salary(salary_data: Dict[str, Any], salary_text: Optional[str]) -> tuple:
    """Parses salary information from Cakeresume's structured data."""
    salary_type_map = {
        'per_month': SalaryType.MONTHLY,
        'per_year': SalaryType.YEARLY,
        'per_hour': SalaryType.HOURLY,
        'per_day': SalaryType.BY_CASE, # Cakeresume API sometimes returns 'per_day'
        'piece_rate_pay': SalaryType.BY_CASE,
    }
    salary_min = salary_data.get('lower_bound')
    salary_max = salary_data.get('upper_bound')
    salary_type = salary_type_map.get(salary_data.get('unit'))
    
    # Fallback/refine salary type from text if API unit is missing or unknown
    if not salary_type and salary_text:
        if "月" in salary_text: salary_type = SalaryType.MONTHLY
        elif "年" in salary_text: salary_type = SalaryType.YEARLY
        elif "時" in salary_text: salary_type = SalaryType.HOURLY
        elif "日" in salary_text: salary_type = SalaryType.BY_CASE # Handle '日薪'
        elif "按件計酬" in salary_text: salary_type = SalaryType.BY_CASE
        elif "面議" in salary_text: salary_type = SalaryType.NEGOTIABLE


    return salary_min, salary_max, salary_type

def transform_script_to_job_model(raw_content: Dict[str, Any], html_content: str, url: str) -> Optional[Job]: # Add html_content
    """
    Parses the job data extracted from the __NEXT_DATA__ script tag.
    """
    # Initialize all potential variables with None to avoid NameError
    title = None
    description = None
    company_name = None
    company_url = None
    company_source_id = None
    location_text = None
    posted_at = None
    salary_text = None
    salary_min = None
    salary_max = None
    salary_type = None
    job_type = None
    experience_required_text = None
    education_required_text = None

    try:
        # raw_content is already a dictionary from __NEXT_DATA__
        job_details = raw_content

        # [關鍵修正] 確保 source_job_id 總是有值，使用 'id' 或從 URL 提取
        source_job_id = str(job_details.get("path")) # Cakeresume uses 'path' as job ID
        if not source_job_id:
            match_id_from_url = re.search(r'jobs/([a-zA-Z0-9_-]+)(?:/?$|\?)', url)
            if match_id_from_url:
                source_job_id = match_id_from_url.group(1)
            else:
                logger.warning(f"[Cakeresume] Could not determine source_job_id from JSON or URL for {url}. Skipping job.")
                return None # If we can't get an ID, we can't save it uniquely.


        title = job_details.get("title")
        # --- Description ---
        description = job_details.get("description") # Try to get full HTML description first
        if not description:
            description = job_details.get("description_plain_text") # Fallback to plain text

        # Ensure description is cleaned of HTML tags if it contains them
        if description:
            description = clean_text(description)

        # Company details
        company_name = None
        company_url = None
        company_source_id = None

        # Try to get company details from 'company' key first
        company_data = job_details.get("company")
        if company_data:
            company_name = company_data.get("name")
            company_path = company_data.get("path")
            if company_path:
                company_url = f"https://www.cakeresume.com/companies/{company_path}"
                company_source_id = company_path
        
        # Fallback to 'page' key if not found in 'company'
        if not company_name and not company_url:
            company_page_data = job_details.get("page", {})
            company_name = company_page_data.get("name")
            company_path = company_page_data.get("path")
            if company_path:
                company_url = f"https://www.cakeresume.com/companies/{company_path}"
                company_source_id = company_path # Use company path as source ID

        # Fallback to extracting company info from URL if not found in JSON
        if not company_name and not company_url:
            match_company_from_url = re.search(r'companies/([a-zA-Z0-9_-]+)/jobs', url)
            if match_company_from_url:
                company_path_from_url = match_company_from_url.group(1)
                company_name = company_path_from_url # Use path as name for now, can be improved later
                company_url = f"https://www.cakeresume.com/companies/{company_path_from_url}"
                company_source_id = company_path_from_url

        # Location
        location_text = None
        html_soup = BeautifulSoup(html_content, "html.parser") # Create soup from html_content

        if flat_locs := job_details.get("flat_location_list_with_locale"):
            if isinstance(flat_locs, list) and flat_locs:
                for loc_entry in flat_locs:
                    if loc_entry.get("zh-tw"):
                        location_text = loc_entry["zh-tw"]
                        break
                if not location_text and flat_locs[0].get("en"):
                    location_text = flat_locs[0].get("en")
        if not location_text and (loc_list := job_details.get("location_list")):
            if isinstance(loc_list, list) and loc_list:
                location_text = loc_list[0]

        # Fallback: Extract location from HTML if not found in JSON
        if not location_text:
            location_tag = html_soup.select_one("div.JobDescriptionRightColumn_locationsWrapper__N_fz_ a")
            if location_tag:
                location_text = clean_text(location_tag.get_text())


        # Posted at
        posted_at_raw = job_details.get("content_updated_at")
        posted_at = None
        if posted_at_raw:
            try:
                # Try parsing as ISO format first (e.g., "2025-07-01T09:00:02.926884Z")
                posted_at = datetime.fromisoformat(posted_at_raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                try:
                    # If ISO parsing fails, try parsing as Unix timestamp (milliseconds)
                    posted_at_timestamp_ms = int(posted_at_raw)
                    posted_at = datetime.fromtimestamp(posted_at_timestamp_ms / 1000)
                except (TypeError, ValueError) as e:
                    logger.warning(f"[Cakeresume] Failed to parse posted_at timestamp {posted_at_raw}: {e}")
        
        # Salary
        salary_min = job_details.get("salary_min")
        salary_max = job_details.get("salary_max")
        salary_type_raw = job_details.get("salary_type")
        salary_currency = job_details.get("salary_currency")

        salary_type_map = {
            'per_month': SalaryType.MONTHLY,
            'per_year': SalaryType.YEARLY,
            'per_hour': SalaryType.HOURLY,
            'per_day': SalaryType.DAILY,
            'piece_rate_pay': SalaryType.BY_CASE,
        }
        salary_type = salary_type_map.get(salary_type_raw)

        # Construct salary_text if min/max/type are available
        if salary_min is not None and salary_max is not None and salary_type:
            if salary_min == salary_max and salary_min == 0 and salary_type == SalaryType.NEGOTIABLE:
                salary_text = "面議"
            elif salary_min == salary_max:
                salary_text = f"{salary_currency} {salary_min}"
            else:
                salary_text = f"{salary_currency} {salary_min}~{salary_max}"
            if salary_type == SalaryType.MONTHLY:
                salary_text += " / 月"
            elif salary_type == SalaryType.YEARLY:
                salary_text += " / 年"
            elif salary_type == SalaryType.HOURLY:
                salary_text += " / 時"
            elif salary_type == SalaryType.DAILY:
                salary_text += " / 日"
        elif salary_type == SalaryType.NEGOTIABLE:
            salary_text = "面議"
        else:
            salary_text = None # Fallback if no structured salary info

        # Job Type
        job_type_raw = job_details.get("job_type")
        job_type_map = {
            "full_time": JobType.FULL_TIME,
            "part_time": JobType.PART_TIME,
            "contract": JobType.CONTRACT,
            "internship": JobType.INTERNSHIP,
            "temporary": JobType.TEMPORARY,
            "freelance": JobType.CONTRACT # Cakeresume uses freelance for contract
        }
        job_type = job_type_map.get(job_type_raw)

        # Experience required text
        min_exp_year = job_details.get("min_work_exp_year")
        if min_exp_year is not None:
            if min_exp_year == 0:
                experience_required_text = "不限年資"
            elif min_exp_year > 0:
                experience_required_text = f"需具備 {int(min_exp_year)} 年以上工作經驗"
        elif job_details.get("requirements_plain_text"):
            exp_match = re.search(r'(\d+)\s*年以上(工作)?經驗', job_details["requirements_plain_text"])
            if exp_match:
                experience_required_text = f"需具備 {exp_match.group(1)} 年以上工作經驗"
            else:
                experience_required_text = clean_text(job_details["requirements_plain_text"])[:50] # Truncate to avoid long text

        # Education required text (not directly available in __NEXT_DATA__ job object, try requirements_plain_text)
        if job_details.get("requirements_plain_text"):
            edu_match = re.search(r'(高中|專科|大學|碩士|博士)', job_details["requirements_plain_text"])
            if edu_match:
                education_required_text = edu_match.group(1)
            else:
                education_required_text = None # No clear education level found

        return Job(
            source_platform=SourcePlatform.PLATFORM_CAKERESUME,
            source_job_id=source_job_id,
            url=url,
            status=JobStatus.ACTIVE,
            title=clean_text(title),
            description=clean_text(description),
            job_type=job_type,
            location_text=location_text,
            posted_at=posted_at,
            salary_text=salary_text,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_type=salary_type,
            experience_required_text=experience_required_text,
            education_required_text=education_required_text,
            company_source_id=company_source_id,
            company_name=clean_text(company_name) if company_name else None,
            company_url=company_url,
        )

    except Exception as e:
        logger.error(f"[Cakeresume] Failed to parse script JSON for url {url}: {e}", exc_info=True)
        return None