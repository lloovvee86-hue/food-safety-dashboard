from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://www.foodsafetykorea.go.kr/portal/specialinfo/searchInfoProduct.do?menu_grp=MENU_NEW04&menu_no=2815')
    inputs = page.locator('input[type="text"]')
    for i in range(inputs.count()):
        el = inputs.nth(i)
        print(f'ID: {el.get_attribute("id")}, Title: {el.get_attribute("title")}')
    browser.close()
