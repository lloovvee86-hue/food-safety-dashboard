import pdfplumber
import sys

def extract_info(pdf_path):
    print(f"--- Extracting {pdf_path} ---")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:3]): # only first 3 pages for preview
                print(f"Page {i+1} Text:")
                print(page.extract_text())
                print(f"Page {i+1} Tables:")
                tables = page.extract_tables()
                for t_idx, table in enumerate(tables):
                    print(f"Table {t_idx+1}:")
                    for row in table[:5]: # preview 5 rows
                        print(row)
                print("-" * 40)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")

if __name__ == "__main__":
    extract_info(r"d:\풀무원\Antigravity\Ladybeg\2025 해충 포획수.pdf")
    extract_info(r"d:\풀무원\Antigravity\Ladybeg\IF-SP-0201 방충방서 관리기준.pdf")
