import pdfplumber

def extract_to_file(pdf_path, out_file):
    out_file.write(f"--- Extracting {pdf_path} ---\n")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                out_file.write(f"\nPage {i+1} Text:\n")
                out_file.write(page.extract_text() or '')
                out_file.write(f"\n\nPage {i+1} Tables:\n")
                tables = page.extract_tables()
                for t_idx, table in enumerate(tables):
                    out_file.write(f"Table {t_idx+1}:\n")
                    for row in table:
                        out_file.write(str(row) + "\n")
                out_file.write("\n" + "-" * 40 + "\n")
    except Exception as e:
        out_file.write(f"Error reading {pdf_path}: {e}\n")

with open(r"d:\풀무원\Antigravity\Ladybeg\pdf_info.txt", "w", encoding="utf-8") as f:
    extract_to_file(r"d:\풀무원\Antigravity\Ladybeg\2025 해충 포획수.pdf", f)
    extract_to_file(r"d:\풀무원\Antigravity\Ladybeg\IF-SP-0201 방충방서 관리기준.pdf", f)
