import json
import time
from playwright.sync_api import sync_playwright
import re

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        keyword = '풀무원'
        print(f"Testing keyword: {keyword}")
        page.goto("https://www.foodsafetykorea.go.kr/portal/specialinfo/searchInfoProduct.do?menu_grp=MENU_NEW04&menu_no=2815", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        search_input = page.locator('#prd_nm')
        search_input.fill(keyword)
        
        with page.expect_response(lambda r: 'searchPrdList' in r.url and r.request.method == 'POST', timeout=15000):
            page.locator('a#srchBtn').click()
            
        page.wait_for_function('document.querySelector("#div_totCnt") && document.querySelector("#div_totCnt").innerText.includes("건이 검색되었습니다")', timeout=15000)
        
        tot_cnt_text = page.locator('#div_totCnt').inner_text()
        print("Tot count text:", tot_cnt_text)
        total_count = 0
        match = re.search(r'총\s*([\d,]+)\s*건', tot_cnt_text)
        if match:
            total_count = int(match.group(1).replace(',', ''))
        
        print("Initial row count:", page.locator("#tbl_prd_list tbody tr").count())
        
        print("Clicking a_list_cnt...")
        page.locator('#a_list_cnt').click()
        page.wait_for_timeout(500)
        
        with page.expect_response(lambda r: 'searchPrdList' in r.url and r.request.method == 'POST', timeout=15000):
            page.locator('a[val="50"]').click()
            
        print("Clicked 50. Waiting for table row count change...")
        
        # Poll the count for up to 10 seconds
        for _ in range(10):
            cnt = page.locator("#tbl_prd_list tbody tr").count()
            print(f"Current row count: {cnt}")
            if cnt == 50 or cnt == total_count:
                break
            page.wait_for_timeout(1000)
            
        browser.close()

if __name__ == "__main__":
    run_test()
