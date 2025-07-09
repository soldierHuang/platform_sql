# crawler/projects/platform_1111/parsers.py
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from bs4 import BeautifulSoup, Tag
from crawler.database.schema import Job
from crawler.enums import SalaryType, JobType, SourcePlatform, JobStatus
from crawler.utils import safe_extract_text, clean_text

logger = logging.getLogger(__name__)

def _parse_date(text: Optional[str]) -> Optional[datetime]:
    """
    從日期字串中解析日期。

    Args:
        text (Optional[str]): 原始日期字串，例如 "2025/06/17 11:24:00" 或 "2025/06/17"。

    Returns:
        Optional[datetime]: 解析後的 datetime 物件，如果無法解析則返回 None。
    """
    if not text:
        return None
    try:
        # 嘗試解析 YYYY/MM/DD HH:MM:SS 格式
        return datetime.strptime(text, "%Y/%m/%d %H:%M:%S")
    except ValueError:
        try:
            # 嘗試解析 YYYY/MM/DD 格式
            return datetime.strptime(text.replace(' ', ''), "%Y/%m/%d")
        except ValueError:
            return None

def _parse_salary(text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    從薪資字串中解析最低和最高薪資。

    Args:
        text (Optional[str]): 原始薪資字串，例如 "月薪 45,000元~55,000元", "面議", "200元以上"。

    Returns:
        Tuple[Optional[int], Optional[int]]: (最低薪資, 最高薪資)。
    """
    if not text:
        return None, None

    # Handle "面議 (經常性薪資達X萬元或以上)" pattern first
    match_negotiable_salary = re.search(r'達(\d+)\s*萬', text)
    if match_negotiable_salary:
        min_salary_in_wan = int(match_negotiable_salary.group(1))
        return min_salary_in_wan * 10000, None # X萬 means X0000, max is None

    # Remove thousand separators and currency units
    cleaned_text = text.replace(',', '').replace('元', '').strip()

    # Look for "X萬" or "X萬元" and convert to full number
    # This handles cases like "月薪 3萬" or "年薪 50萬元"
    match_wan = re.search(r'(\d+)\s*萬', cleaned_text)
    if match_wan:
        value_in_wan = int(match_wan.group(1))
        # Replace "X萬" with "X0000" to allow general digit extraction to work
        cleaned_text = cleaned_text.replace(match_wan.group(0), str(value_in_wan * 10000))

    # Find all numbers
    nums = [int(n) for n in re.findall(r'\d+', cleaned_text)]

    if not nums:
        if "面議" in text:
            return None, None
        return None, None

    if len(nums) == 1:
        min_salary = nums[0]
        max_salary = None
        if "以上" in text or "起" in text:
            max_salary = None
        else:
            max_salary = min_salary
        return min_salary, max_salary

    if len(nums) >= 2:
        return nums[0], nums[1]

    return None, None

def _find_detail_item(soup: BeautifulSoup, label: str) -> Optional[Tag]:
    """
    在詳情頁中找到對應標籤（例如 "工作性質", "上班地點"）的容器。
    此函數會尋找包含指定 `label` 文字的標籤，然後嘗試獲取其內容或其兄弟標籤的內容。

    Args:
        soup (BeautifulSoup): 職缺詳情頁的 BeautifulSoup 物件。
        label (str): 要查找的標籤文字。

    Returns:
        Optional[Tag]: 包含目標內容的 BeautifulSoup Tag 物件，如果找不到則返回 None。
    """
    # Try to find h3 with the label and return its next sibling
    h3_tag = soup.find("h3", string=lambda text: text and label in text)
    if h3_tag:
        next_sibling = h3_tag.find_next_sibling()
        if next_sibling and next_sibling.get_text(strip=True):
            return next_sibling

    # Fallback to original broader search if h3 sibling not found
    label_tag = soup.find(lambda tag: tag.name in ['div', 'span', 'dt', 'p'] and label in tag.get_text(strip=True))
    if label_tag:
        if label_tag.name == 'dt':
            next_dd = label_tag.find_next_sibling('dd')
            if next_dd and next_dd.get_text(strip=True):
                return next_dd
        
        next_sibling = label_tag.find_next_sibling()
        if next_sibling and next_sibling.get_text(strip=True):
            return next_sibling
        
        parent = label_tag.find_parent()
        if parent:
            for child in parent.find_all(lambda tag: tag.name in ['div', 'span', 'p'], recursive=False):
                if child != label_tag and child.get_text(strip=True) and not child.find(label_tag.name, string=label):
                    return child
            for child in parent.find_all(lambda tag: tag.name in ['div', 'span', 'p']):
                if child != label_tag and child.get_text(strip=True):
                    return child
    return None

def transform_categories_to_source_model(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    從 API 響應中提取 'jobPosition' 列表並轉換為資料庫模型。

    Args:
        raw_data (Dict[str, Any]): 從 1111 `/api/v1/codeCategories/` 獲取的原始 JSON 數據。

    Returns:
        List[Dict[str, Any]]: 扁平化的 CategorySource 數據字典列表。
    """
    categories_from_api = raw_data.get('jobPosition', [])
    if not categories_from_api:
        logger.warning("[1111] 在 API 分類數據中未找到 'jobPosition' 鍵或其為空。")
        return []
        
    flat_list = []
    for item in categories_from_api:
        code = item.get("code")
        name = item.get("name")
        parent_code = item.get("parentCode")

        if code and name:
            flat_list.append({
                "source_platform": SourcePlatform.PLATFORM_1111,
                "source_category_id": code,
                "source_category_name": name,
                # '0' 表示沒有父級，將其轉換為 None
                "parent_source_id": parent_code if parent_code and parent_code != "0" else None,
            })
                
    logger.info(f"[1111] 從 API 響應中成功提取 {len(flat_list)} 個分類。")
    return flat_list

def transform_details_to_job_model(intermediate_data: Dict[str, Any], html_content: str, url: str) -> Optional[Job]:
    """
    將 1111 的職缺詳情 HTML 和 API 中介數據轉換為標準化的 Job 模型。
    
    核心邏輯：優先使用 `intermediate_data` 中的公司名和 Job ID，
    其他詳情從 HTML 中解析。對薪資、地點等字段進行魯棒性提取。
    
    Args:
        intermediate_data (Dict[str, Any]): 從列表 API 獲取並存儲在 Redis 的中介數據。
        html_content (str): 職缺詳情頁的完整 HTML 內容。
        url (str): 該職缺的原始 URL。

    Returns:
        Optional[Job]: 一個填充了數據的 Job 物件。

    Raises:
        ValueError: 如果 HTML 中缺少標題等關鍵信息，或 `intermediate_data` 不足。
    """
    if not intermediate_data or not intermediate_data.get("jobId"):
        logger.error(f"[1111] 缺少來自列表 API 的中介數據或 jobId，無法解析 URL: {url}.")
        raise ValueError("缺少來自列表 API 的中介數據 (intermediate_data) 或 jobId。")

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 職缺標題：多個選擇器，優先級從高到低
        title_tag = soup.select_one("main h1") # 新版頁面的標題選擇器
        if not title_tag:
            # 舊版頁面標題選擇器 (如果新版失敗)
            title_tag = soup.select_one("div.job_content_header h1") 
        if not title_tag:
            logger.warning(f"[1111] HTML 中缺少職缺標題 (h1 標籤)，URL: {url}。")
            raise ValueError("HTML 中缺少職缺標題 (h1 標籤)。")
        
        title = clean_text(title_tag.text)

        # 職缺描述：多個選擇器，更魯棒
        description_content = soup.select_one(".job_description") or \
                              soup.select_one("div.job-content__description") or \
                              soup.select_one("div.job-detail-content") or \
                              soup.select_one("div.job-description-container") or \
                              soup.select_one("div#main-content") or \
                              soup.select_one("div.content") or \
                              soup.select_one("body") # 最終回退到主內容區
        description = safe_extract_text(description_content)

        # 公司名稱：優先從 intermediate_data 獲取 (Q-001 修正)
        company_name = intermediate_data.get("companyName")
        company_id = intermediate_data.get("companyId")
        company_url = f"https://www.1111.com.tw/corp/{company_id}" if company_id else None

        # 提取詳細信息 - 使用新函數並處理潛在的缺失值
        job_type_text = None
        if job_type_tag := _find_detail_item(soup, "工作性質"):
            job_type_text = safe_extract_text(job_type_tag)

        location_text = None
        if location_tag := _find_detail_item(soup, "工作地點"):
            # 清理掉可能存在的"地圖"字樣
            location_text = clean_text(location_tag.text.split('地圖')[0])

        salary_text = None
        if salary_tag := _find_detail_item(soup, "工作待遇"):
            # 清理掉可能存在的"查看薪資水平"字樣
            salary_text = clean_text(salary_tag.text.split('查看薪資水平')[0])
        
        salary_min, salary_max = _parse_salary(salary_text)
        
        salary_type = SalaryType.NEGOTIABLE # 默認值
        if salary_text:
            if "月薪" in salary_text:
                salary_type = SalaryType.MONTHLY
            elif "年薪" in salary_text:
                salary_type = SalaryType.YEARLY
            elif "時薪" in salary_text:
                salary_type = SalaryType.HOURLY
            elif "日薪" in salary_text:
                salary_type = SalaryType.DAILY
            elif "論件計酬" in salary_text or "按件計酬" in salary_text:
                salary_type = SalaryType.BY_CASE
            elif "面議" in salary_text:
                salary_type = SalaryType.NEGOTIABLE

        job_type = None
        if job_type_text:
            if "全職" in job_type_text:
                job_type = JobType.FULL_TIME
            elif "兼職" in job_type_text or "工讀" in job_type_text:
                job_type = JobType.PART_TIME
            elif "派遣" in job_type_text or "約聘" in job_type_text:
                job_type = JobType.CONTRACT
            elif "實習" in job_type_text:
                job_type = JobType.INTERNSHIP

        experience_required_text = None
        if exp_tag := _find_detail_item(soup, "工作經驗"):
            experience_required_text = safe_extract_text(exp_tag)
            # 處理 "Top" 或其他可能表示 "不拘" 的文本 (Q-003 修正)
            if experience_required_text and experience_required_text.lower() in ["top", "不拘", "無經驗"]:
                experience_required_text = None # 設定為 None 表示不拘
            elif experience_required_text and experience_required_text.startswith("需具備"): # 避免重複前綴
                pass
            elif experience_required_text: # 嘗試從數字文本中正規化
                match_exp = re.search(r'(\d+)\s*年以上', experience_required_text)
                if match_exp:
                    experience_required_text = f"需具備 {match_exp.group(1)} 年以上工作經驗"
                else: # 如果沒有匹配到，且不是不拘等，就直接使用原文本
                    experience_required_text = clean_text(experience_required_text)  # 使用原文本
            else: # 如果為空，設定為 None
                experience_required_text = None

        education_required_text = None
        if edu_tag := _find_detail_item(soup, "學歷要求"):
            education_required_text = safe_extract_text(edu_tag)
            # 處理 "Top" 或其他可能表示 "不拘" 的文本 (Q-003 修正)
            if education_required_text and education_required_text.lower() in ["top", "不拘", "不限"]:
                education_required_text = None
            elif education_required_text: # 嘗試從學歷關鍵字中正規化
                edu_map = {"大學": "大學", "專科": "專科", "高中": "高中職", "碩士": "碩士", "博士": "博士"}
                found_edu = next((v for k, v in edu_map.items() if k in education_required_text), None)
                if found_edu:
                    education_required_text = f"{found_edu}以上"
                else: # 如果沒有匹配到，且不是不拘等，就直接使用原文本
                    education_required_text = clean_text(education_required_text) # 使用原文本
            else: # 如果為空，設定為 None
                education_required_text = None

        # Extract posted_at
        posted_at = None
        # Find the <li> that contains "更新日期"
        update_date_h3 = soup.find("h3", string=lambda text: text and "更新日期" in text)
        if update_date_h3:
            li_parent = update_date_h3.find_parent("li")
            if li_parent:
                time_tag = li_parent.find("time")
                if time_tag and time_tag.get("datetime"):
                    posted_at_text = time_tag["datetime"]
                    posted_at = _parse_date(posted_at_text)

        return Job(
            source_platform=SourcePlatform.PLATFORM_1111,
            source_job_id=str(intermediate_data["jobId"]), # 優先使用 API 提供的 jobId
            url=url,
            status=JobStatus.ACTIVE,
            title=title,
            description=description,
            job_type=job_type,
            location_text=location_text,
            posted_at=posted_at,
            salary_text=salary_text,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_type=salary_type,
            experience_required_text=experience_required_text,
            education_required_text=education_required_text,
            company_source_id=str(company_id) if company_id else None, # 優先使用 API 提供的 companyId
            company_name=company_name, # 優先使用 API 提供的 companyName
            company_url=company_url,
        )
    except Exception as e:
        logger.error(f"[1111] Parser 失敗於 URL {url}: {e}", exc_info=True)
        raise # 重新拋出異常，讓 Orchestrator 統一處理失敗狀態