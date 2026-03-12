"""
구글 스프레드시트 자동 업로드 스크립트
- food_data.csv 데이터를 구글 스프레드시트에 자동으로 업로드합니다.
- 서비스 계정(JSON 키)으로 인증하므로 브라우저 로그인이 필요 없습니다.
"""

import csv
import os
import glob
import gspread
from google.oauth2.service_account import Credentials

# ============================
# 설정값 (필요에 따라 수정)
# ============================
SPREADSHEET_NAME = "풀무원 식품안전 데이터"  # 생성될 스프레드시트 이름
CSV_FILE = "food_data.csv"
SHEET_NAME = "식품데이터"

# 서비스 계정 키 파일 자동 탐색
def find_service_account_key():
    """프로젝트 폴더에서 서비스 계정 JSON 키 파일을 자동으로 찾습니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    patterns = [
        os.path.join(script_dir, "*service*.json"),
        os.path.join(script_dir, "*kodari*.json"),
        os.path.join(script_dir, "*credentials*.json"),
    ]
    for pattern in patterns:
        files = glob.glob(pattern)
        # client_secret 파일은 제외 (OAuth용이므로)
        files = [f for f in files if "client_secret" not in os.path.basename(f)]
        if files:
            return files[0]
    return None


def authenticate():
    """서비스 계정으로 Google API 인증"""
    key_file = find_service_account_key()
    if not key_file:
        print("❌ 서비스 계정 JSON 키 파일을 찾을 수 없습니다!")
        print("   프로젝트 폴더에 서비스 계정 키 파일을 넣어주세요.")
        print("   (파일명에 'service', 'kodari', 또는 'credentials'가 포함되어야 합니다)")
        return None

    print(f"🔑 서비스 계정 키 파일: {os.path.basename(key_file)}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_file(key_file, scopes=scopes)
    client = gspread.authorize(credentials)
    print("✅ Google API 인증 성공!")
    return client


def read_csv(file_path):
    """CSV 파일 읽기"""
    if not os.path.exists(file_path):
        print(f"❌ CSV 파일을 찾을 수 없습니다: {file_path}")
        return None

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        data = list(reader)

    print(f"📊 CSV 데이터 로드 완료: {len(data) - 1}개 행 (헤더 제외)")
    return data


def upload_to_sheets(client, data):
    """구글 스프레드시트에 데이터 업로드"""
    # 스프레드시트 열기 또는 생성
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        print(f"📋 기존 스프레드시트 열기: {SPREADSHEET_NAME}")
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SPREADSHEET_NAME)
        print(f"📋 새 스프레드시트 생성: {SPREADSHEET_NAME}")
        # 서비스 계정이 만든 스프레드시트는 본인만 접근 가능하므로
        # 대표님 이메일로 공유 설정 (편집 권한)
        spreadsheet.share("lloovvee86@gmail.com", perm_type="user", role="writer")
        print("📧 lloovvee86@gmail.com 에게 편집 권한 공유 완료!")

    # 시트 열기 또는 생성
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        print(f"📄 기존 시트 열기: {SHEET_NAME}")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=len(data) + 10, cols=len(data[0]) + 2)
        print(f"📄 새 시트 생성: {SHEET_NAME}")

    # 기존 데이터 모두 지우고 새 데이터로 교체
    worksheet.clear()
    print("🗑️  기존 데이터 클리어 완료")

    # 데이터 한 번에 업로드 (batch update로 빠르게)
    worksheet.update(data, value_input_option="USER_ENTERED")
    print(f"✅ {len(data) - 1}개 행 업로드 완료!")

    # 스프레드시트 URL 출력
    print(f"\n🔗 스프레드시트 URL: {spreadsheet.url}")
    return spreadsheet.url


def main():
    print("=" * 50)
    print("🐟 코다리 부장의 스프레드시트 자동 업로드 🐟")
    print("=" * 50)

    # 1. 인증
    client = authenticate()
    if not client:
        return

    # 2. CSV 읽기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, CSV_FILE)
    data = read_csv(csv_path)
    if not data:
        return

    # 3. 업로드
    url = upload_to_sheets(client, data)

    print("\n" + "=" * 50)
    print("🎉 모든 작업 완료!")
    print(f"📊 스프레드시트: {SPREADSHEET_NAME}")
    print(f"🔗 URL: {url}")
    print("=" * 50)


if __name__ == "__main__":
    main()
