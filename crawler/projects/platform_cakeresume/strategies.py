# crawler/projects/platform_cakeresume/strategies.py
"""
Strategies for Cakeresume, featuring a robust HTML-based UrlFetcher
and a script-parsing DetailParser.
"""
import logging
from typing import Dict, Any, Generator, Optional, List
import json

from bs4 import BeautifulSoup
from crawler.core.protocols import UrlFetcher, DetailFetcher, DetailParser
from crawler.utils import make_request
from crawler.database.schema import Job, CategorySource
from . import parsers

logger = logging.getLogger(__name__)

class HtmlUrlFetcher:
    """
    Strategy Implementation: Fetches job URLs by scraping the
    category-specific HTML pages, as the search API is not available.
    """
    def __init__(self, categories: List[CategorySource], settings: Any):
        # We only need sub-categories that have an actual ID
        self.categories = [cat for cat in categories if cat.parent_source_id]
        self.cfg = settings
        self.base_url = "https://www.cakeresume.com"

    def __call__(self) -> Generator[Dict[str, Any], None, None]:
        if not self.categories:
            logger.warning("[Cakeresume] No categories provided to UrlFetcher. Skipping.")
            return

        logger.info(f"[Cakeresume] Starting to fetch from HTML pages for {len(self.categories)} categories.")
        
        for category in self.categories:
            category_id = category.source_category_id
            target_url = f"{self.base_url}/jobs/categories/{category_id}"
            
            # Cakeresume uses infinite scroll, we can simulate it by adding `page` param
            for page in range(1, self.cfg.max_pages + 1):
                params = {'page': page}
                logger.debug(f"[Cakeresume] Fetching page {page} for category: {category_id}")
                try:
                    res = make_request(
                        target_url,
                        headers=self.cfg.headers,
                        params=params
                    )
                    
                    soup = BeautifulSoup(res.text, "html.parser")
                    # Use the correct selector for job links
                    job_links = soup.select("a.JobSearchItem_jobTitle__bu6yO")
                    
                    if not job_links:
                        logger.info(f"[Cakeresume] No more jobs found for category {category_id} at page {page}.")
                        break
                    
                    for link in job_links:
                        if href := link.get('href'):
                            # The href is a relative path, e.g., /companies/company/jobs/job-id
                            # The orchestrator will handle joining it with the base URL
                            yield {'href': href}

                except Exception as e:
                    logger.error(f"[Cakeresume] Failed to fetch HTML for category {category_id}, page {page}: {e}", exc_info=True)
                    break


class HtmlDetailFetcher:
    """Strategy: Fetches the full HTML of a single job detail page."""
    def __init__(self, settings: Any):
        self.cfg = settings

    def __call__(self, url: str) -> str:
        try:
            res = make_request(url, headers=self.cfg.headers)
            return res.text
        except Exception as e:
            logger.error(f"[Cakeresume] Failed to fetch detail for url {url}: {e}")
            return ""

class ScriptDetailParser:
    """
    Strategy: Finds the <script type="application/ld+json"> tag in the
    raw HTML content and passes its content to a dedicated parser.
    """
    def __call__(self, raw_content: str, url: str, intermediate_data: Optional[Dict[str, Any]]) -> Optional[Job]:
        soup = BeautifulSoup(raw_content, "html.parser")
        
        # Cakeresume detail pages embed job data in a script tag with id="__NEXT_DATA__"
        script_tag = soup.find("script", id="__NEXT_DATA__")
        
        if not script_tag or not script_tag.string:
            logger.warning(f"[Cakeresume] Could not find __NEXT_DATA__ script tag or it is empty on page: {url}")
            return None
        
        try:
            next_data = json.loads(script_tag.string)
            # The actual job data is usually nested under props.pageProps.job
            job_data = next_data.get("props", {}).get("pageProps", {}).get("job")
            
            if not job_data:
                logger.warning(f"[Cakeresume] Could not find job data within __NEXT_DATA__ for page: {url}")
                return None
            
            # Pass the extracted job_data (dict) and the original raw_content (HTML) to the parser
            return parsers.transform_script_to_job_model(job_data, raw_content, url) # Pass raw_content here
        except json.JSONDecodeError as e:
            logger.error(f"[Cakeresume] Failed to decode __NEXT_DATA__ JSON for url {url}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"[Cakeresume] An unexpected error occurred while processing __NEXT_DATA__ for url {url}: {e}", exc_info=True)
            return None