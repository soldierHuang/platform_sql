# crawler/projects/platform_1111/test_1111_parser.py (Diagnostic Version)
import requests
import pprint
import urllib3
import re
from bs4 import BeautifulSoup
from crawler.projects.platform_1111.parsers import transform_details_to_job_model
from crawler.utils import clean_text
from crawler.settings import settings

TEST_URL = "https://www.1111.com.tw/job/103687212"

def run_diagnostic():
    print(f"[*] Running DIAGNOSTIC test with URL: {TEST_URL}")

    try:
        # 1. 獲取 HTML
        response = requests.get(TEST_URL, headers=settings.p1111.headers, verify=False)
        response.raise_for_status()
        html_content = response.text
        print("[*] Successfully fetched HTML content.")

        # 2. 保存 HTML 以供手動檢查
        debug_filename = "debug_1111.html"
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[*] Fetched HTML has been saved to '{debug_filename}'. Please inspect this file.")

        # 3. 執行深度診斷
        soup = BeautifulSoup(html_content, "html.parser")
        print("\n--- START OF DEBUG ---")
        company_link_tag = soup.select_one("main a[href^='/corp/']")
        if company_link_tag:
            print("[DEBUG] Found the company link tag:")
            print(str(company_link_tag))
            print("\n[DEBUG] Raw text content of the tag (using repr to see hidden chars):")
            print(repr(company_link_tag.get_text()))
        else:
            print("[DEBUG] FAILED to find the company link tag with selector: main a[href^='/corp/']")
        print("--- END OF DEBUG ---\n")

        # 4. 再次嘗試解析
        print("[*] Now attempting to parse with the main function...")
        # 模擬真實場景：假設我們從列表 API 獲取了 companyName
        mock_api_data = {"companyName": "盈弘展工程行 (from API)"}
        job_object = transform_details_to_job_model(
            api_data=mock_api_data,
            html_content=html_content,
            url=TEST_URL
        )
        
        if job_object:
            print("\n[SUCCESS] Parser function finished.")
            pprint.pprint(job_object.model_dump())
            if job_object.company_name:
                print("\n[FINAL VERDICT] SUCCESS: Company name was populated correctly!")
            else:
                print("\n[FINAL VERDICT] FAILURE: Company name is still None, even with API fallback.")
        else:
            print("\n[FAILURE] Parser function returned None.")

    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    run_diagnostic()