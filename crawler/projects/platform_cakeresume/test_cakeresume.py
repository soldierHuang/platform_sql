
import pytest
import json
from unittest.mock import MagicMock
from bs4 import BeautifulSoup

from crawler.database.schema import Job
from crawler.enums import SourcePlatform, JobStatus, SalaryType, JobType
from crawler.projects.platform_cakeresume.parsers import transform_details_to_job_model
from crawler.projects.platform_cakeresume.strategies import HtmlUrlFetcher, HtmlDetailFetcher, ScriptDetailParser
from crawler.settings import Settings, ProjectCakeresumeSettings

# Mock settings for testing
@pytest.fixture
def mock_cakeresume_settings():
    return ProjectCakeresumeSettings(
        max_pages=1,
        max_workers=1,
        headers={"User-Agent": "test-agent"}
    )

# Test for parsers.py
def test_transform_details_to_job_model_success():
    """Test successful parsing of Cakeresume HTML content."""
    mock_html_content = """
    <html>
    <body>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "job": {
                        "path": "test-job-id",
                        "title": "Test Job Title",
                        "description_plain": "This is a test description.",
                        "salary_type": "per_month",
                        "salary_min": 50000,
                        "salary_max": 80000,
                        "salary_currency": "TWD",
                        "job_type": "full_time",
                        "locations": [{"name": "Taipei"}, {"name": "New Taipei"}],
                        "company": {
                            "name": "Test Company",
                            "path": "test-company-path"
                        }
                    }
                }
            }
        }
        </script>
    </body>
    </html>
    """
    url = "https://www.cakeresume.com/jobs/test-job-id"
    job = transform_details_to_job_model(mock_html_content, url)

    assert job is not None
    assert job.source_platform == SourcePlatform.PLATFORM_CAKERESUME
    assert job.source_job_id == "test-job-id"
    assert job.url == url
    assert job.status == JobStatus.ACTIVE
    assert job.title == "Test Job Title"
    assert job.description == "This is a test description."
    assert job.salary_type == SalaryType.MONTHLY
    assert job.salary_min == 50000
    assert job.salary_max == 80000
    assert job.salary_text == "50000 - 80000 TWD"
    assert job.job_type == JobType.FULL_TIME
    assert job.location_text == "Taipei, New Taipei"
    assert job.company_name == "Test Company"
    assert job.company_url == "https://www.cakeresume.com/companies/test-company-path"

def test_transform_details_to_job_model_no_next_data():
    """Test parsing when __NEXT_DATA__ script tag is missing."""
    mock_html_content = "<html><body><h1>No Job Data</h1></body></html>"
    url = "https://www.cakeresume.com/jobs/test-job-id"
    with pytest.raises(ValueError, match="在 HTML 中未找到 `__NEXT_DATA__` script 標籤。"):
        transform_details_to_job_model(mock_html_content, url)

def test_transform_details_to_job_model_no_job_data():
    """Test parsing when 'job' data is missing in __NEXT_DATA__."""
    mock_html_content = """
    <html>
    <body>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {}
            }
        }
        </script>
    </body>
    </html>
    """
    url = "https://www.cakeresume.com/jobs/test-job-id"
    with pytest.raises(ValueError, match="在 `__NEXT_DATA__` JSON 中未找到 'job' 核心數據區塊。"):
        transform_details_to_job_model(mock_html_content, url)

def test_transform_details_to_job_model_invalid_json():
    """Test parsing with invalid JSON in __NEXT_DATA__."""
    mock_html_content = """
    <html>
    <body>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "job": {
                        "path": "test-job-id",
                        "title": "Test Job Title"
                    }
                }
            }
        }
        </script>
    </body>
    </html>
    """
    url = "https://www.cakeresume.com/jobs/test-job-id"
    job = transform_details_to_job_model(mock_html_content, url)
    assert job.title == "Test Job Title"
    assert job.description is None # description_plain is missing

# Test for strategies.py
def test_html_url_fetcher_success(mock_cakeresume_settings, monkeypatch):
    """Test HtmlUrlFetcher successfully extracts job URLs."""
    mock_response_text = """
    <html>
    <body>
        <a href="/companies/company-a/jobs/job-1">Job 1</a>
        <a href="/companies/company-b/jobs/job-2">Job 2</a>
    </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = mock_response_text
    monkeypatch.setattr("crawler.projects.platform_cakeresume.strategies.make_request", lambda url, headers: mock_response)

    fetcher = HtmlUrlFetcher(mock_cakeresume_settings)
    urls = list(fetcher())
    
    assert len(urls) == 2
    assert {"href": "/companies/company-a/jobs/job-1"} in urls
    assert {"href": "/companies/company-b/jobs/job-2"} in urls

def test_html_url_fetcher_no_links(mock_cakeresume_settings, monkeypatch):
    """Test HtmlUrlFetcher when no job links are found."""
    mock_response_text = "<html><body><h1>No Links</h1></body></html>"
    mock_response = MagicMock()
    mock_response.text = mock_response_text
    monkeypatch.setattr("crawler.projects.platform_cakeresume.strategies.make_request", lambda url, headers: mock_response)

    fetcher = HtmlUrlFetcher(mock_cakeresume_settings)
    urls = list(fetcher())
    assert len(urls) == 0

def test_html_detail_fetcher_success(mock_cakeresume_settings, monkeypatch):
    """Test HtmlDetailFetcher successfully fetches HTML content."""
    mock_html_content = "<html><body><h1>Job Details</h1></body></html>"
    mock_response = MagicMock()
    mock_response.text = mock_html_content
    monkeypatch.setattr("crawler.projects.platform_cakeresume.strategies.make_request", lambda url, headers: mock_response)

    fetcher = HtmlDetailFetcher(mock_cakeresume_settings)
    content = fetcher("https://www.cakeresume.com/jobs/test-job")
    assert content == mock_html_content

def test_script_detail_parser_success(mock_cakeresume_settings):
    """Test ScriptDetailParser successfully parses HTML content."""
    mock_html_content = """
    <html>
    <body>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "job": {
                        "path": "parsed-job-id",
                        "title": "Parsed Job Title",
                        "description_plain": "This is a parsed description.",
                        "salary_type": "per_year",
                        "salary_min": 600000,
                        "salary_max": 1000000,
                        "salary_currency": "TWD",
                        "job_type": "contract",
                        "locations": [{"name": "Kaohsiung"}],
                        "company": {
                            "name": "Parsed Company",
                            "path": "parsed-company-path"
                        }
                    }
                }
            }
        }
        </script>
    </body>
    </html>
    """
    url = "https://www.cakeresume.com/jobs/parsed-job-id"
    parser = ScriptDetailParser()
    job = parser(mock_html_content, url, None)

    assert job is not None
    assert job.title == "Parsed Job Title"
    assert job.salary_type == SalaryType.YEARLY
    assert job.company_name == "Parsed Company"
