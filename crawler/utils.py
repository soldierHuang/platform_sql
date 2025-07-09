# crawler/utils.py
"""
此模組提供全域的通用工具函數，以遵循 DRY (Don't Repeat Yourself) 原則。
"""
import logging
import requests
from typing import Callable, Iterable, Any, Generator, Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

def run_concurrently(
    func: Callable[..., Any],
    tasks: List[Any],
    max_workers: int
) -> Generator[Any, None, None]:
    """
    以線程池併發執行任務。
    """
    if not tasks:
        # yield from () 是一個返回空生成器的簡潔寫法
        yield from ()
        return
        
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(func, task): task for task in tasks}
        
        for future in as_completed(future_to_task):
            task_repr = repr(future_to_task[future])[:100]
            try:
                yield future.result()
            except Exception as exc:
                logger.error(f"Error in concurrent task '{task_repr}': {exc}", exc_info=True)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def make_request(
    url: str,
    headers: Dict,
    method: str = "GET",
    params: Optional[Dict] = None,
    timeout: int = 20,
    **kwargs
) -> requests.Response:
    """
    一個帶有重試機制的健壯的網絡請求函數。
    """
    try:
        # [確認] kwargs 允許我們傳遞 verify=False 等參數
        logger.debug(f"Making {method} request to {url} with params: {params} and kwargs: {kwargs}")
        response = requests.request(method, url, headers=headers, params=params, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.warning(f"Request failed for {url} with params {params}. Error: {e}. Retrying...")
        raise

from bs4 import BeautifulSoup # Add this import

# ... (other functions remain the same)

def clean_text(text: Optional[str]) -> Optional[str]:
    if isinstance(text, str):
        # First, remove HTML tags
        soup = BeautifulSoup(text, "html.parser")
        cleaned_text = soup.get_text()
        # Then, remove extra whitespace and strip leading/trailing whitespace
        return ' '.join(cleaned_text.split()).strip()
    return text

def safe_extract_text(tag: Optional[Tag], default: Optional[str] = None) -> Optional[str]:
    if isinstance(tag, Tag):
        return clean_text(tag.get_text())
    return default