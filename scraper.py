import csv
import time
import os
import glob
from playwright.sync_api import sync_playwright

def scrape_korea_food_safety():
    keywords = ['풀무원', '풀스키친', '풀스쿡']
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in keywords:
            print(f"Scraping for keyword: {keyword}")
            page.goto("https://www.foodsafetykorea.go.kr/portal/specialinfo/searchInfoProduct.do?menu_grp=MENU_NEW04&menu_no=2815", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            try:
                # 1. 검색어 입력 (제품명 입력란) - id가 prd_nm 임
                search_input = page.locator('#prd_nm')
                search_input.fill("") # Clear before filling, just in case
                search_input.fill(keyword)
                
                # 2. 검색 버튼 클릭
                with page.expect_response(lambda r: 'searchPrdList' in r.url and r.request.method == 'POST', timeout=45000):
                    page.locator('a#srchBtn').click()
                
                print("Waiting for initial results to load...")
                page.wait_for_function('document.querySelector("#div_totCnt") && document.querySelector("#div_totCnt").innerText.includes("건이 검색되었습니다")', timeout=45000)
                
                # 총 검색 건수 파악
                total_count = 0
                tot_cnt_text = page.locator('#div_totCnt').inner_text()
                import re
                match = re.search(r'총\s*([\d,]+)\s*건', tot_cnt_text)
                if match:
                    total_count = int(match.group(1).replace(',', ''))
                print(f"[{keyword}] Expected total count: {total_count}")
                if total_count == 0:
                    print(f"No results found for {keyword}")
                    continue
                
                # 3. 50개씩 보기로 변경 (드롭다운 누르고 50개씩 선택)
                print("Changing to 50 items per page...")
                page.locator('#a_list_cnt').click() # 드롭다운 열기
                page.wait_for_timeout(500)
                with page.expect_response(lambda r: 'searchPrdList' in r.url and r.request.method == 'POST', timeout=45000):
                    page.locator('a[val="50"]').click() # 50개 선택
                
                print("50 items list loaded. Waiting for DOM update...")
                
                # Check how many items we expect on the first page
                expected_rows_on_page_1 = 50 if total_count >= 50 else total_count
                
                print(f"Waiting for precisely {expected_rows_on_page_1} rows to render...")
                try:
                    # 렌더링에 시간이 꽤 걸릴 수 있으므로 넉넉하게 45초 확보
                    page.wait_for_function(f'document.querySelectorAll("#tbl_prd_list tbody tr").length === {expected_rows_on_page_1}', timeout=45000)
                except Exception as e:
                    print(f"Warning: waiting for {expected_rows_on_page_1} rows timed out, giving extra 10 seconds...", e)
                    page.wait_for_timeout(10000) # 타임아웃 되더라도 최후의 10초 무조건 대기
                    
                page.wait_for_timeout(2000) # 렌더링 후 안정화를 위한 2초 대기
                
            except Exception as e:
                print(f"Error initiating search for {keyword}: {e}")
                continue

            # 페이지 순회하며 크롤링
            page_num = 1
            keyword_results_count = 0
            while True:
                print(f"Scraping page {page_num} for {keyword}")
                try:
                    # 각 페이지별로 스크린샷 캡처 (전체 화면)
                    screenshot_path = f"{keyword}_page{page_num}.png"
                    
                    # 로딩 중인지 확인 (번호 셀에 'loading' 텍스트가 사라질 때까지 대기)
                    try:
                        page.wait_for_function('!document.querySelector("#tbl_prd_list tbody tr td").innerText.toLowerCase().includes("loading")', timeout=45000)
                    except Exception as e:
                        print("Timeout waiting for 'loading...' to disappear, proceeding anyway.", e)
                        
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"Screenshot saved: {screenshot_path}")

                    rows = page.locator("#tbl_prd_list tbody tr")
                    count = rows.count()
                    for i in range(count):
                        row = rows.nth(i)
                        
                        # 식품안전나라 모바일/PC 반응형 테이블 구조 반영 (span.table_txt 내부에 데이터 존재)
                        cols = row.locator("td")
                        
                        col_texts = []
                        for j in range(cols.count()):
                            td = cols.nth(j)
                            # 모바일 구조(span.table_txt)이거나 일반 텍스트일 수 있음
                            if td.locator('span.table_txt').count() > 0:
                                col_texts.append(td.locator('span.table_txt').first.inner_text().strip())
                            else:
                                col_texts.append(td.inner_text().strip())
                        
                        if len(col_texts) > 1 and "조회된 데이터가 없습니다" not in col_texts[0] and "조회결과가 없습니다" not in col_texts[0]:
                            results.append([keyword] + col_texts)
                            keyword_results_count += 1
                except Exception as e:
                    print("Error parsing rows:", e)
                    break
                    
                # 모든 건수를 수집했으면 조기 종료
                if keyword_results_count >= total_count:
                    print(f"Finished collecting all {keyword_results_count} items for {keyword}")
                    break

                # 다음 페이지 버튼 처리
                try:
                    next_page_num = page_num + 1
                    # title 속성이 없을 수 있으므로 텍스트로도 같이 찾기
                    next_btn = page.locator(f'a.page-link[title="{next_page_num}"]')
                    if next_btn.count() == 0:
                        next_btn = page.locator(f'a.page-link:text-is("{next_page_num}")')
                    
                    # 현재 활성화된 다음 버튼이 있는지 확인
                    if next_btn.count() > 0 and next_btn.first.is_visible():
                        print(f"Moving to page {next_page_num}...")
                        with page.expect_response(lambda r: 'searchPrdList' in r.url and r.request.method == 'POST', timeout=45000):
                            next_btn.first.click()
                        page.wait_for_timeout(2000) # 버튼 클릭 후 렌더링 대기
                        page_num += 1
                    else:
                        break # 다음 페이지가 없으면 종료
                except Exception as e:
                    print("Pagination ended:", e)
                    break

        browser.close()

    if results:
        with open("food_data.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["검색어", "번호", "품목보고번호", "업체명", "품목유형", "소비기한", "제품명", "분류"])
            for r in results:
                writer.writerow(r)
        print("Data successfully saved to food_data.csv")
    else:
        print("No data collected.")

    print("Cleaning up png files...")
    png_files = glob.glob("*.png")
    for file in png_files:
        try:
            os.remove(file)
            print(f"Deleted {file}")
        except Exception as e:
            print(f"Error deleting {file}: {e}")

if __name__ == "__main__":
    scrape_korea_food_safety()
