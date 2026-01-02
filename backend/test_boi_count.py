# backend/test_boi_count.py
import pdfplumber
from pathlib import Path

pdf_path = Path("data/raw_pdfs/bank_of_india/BOI_Statement_AARAV_NAIR_150_Entries.pdf")

print(f"Testing: {pdf_path.name}")
print("=" * 60)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    
    total_transactions = 0
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        print(f"\nPage {page_num}: {len(tables)} table(s)")
        
        for t_idx, table in enumerate(tables):
            if table:
                # Count data rows (skip header)
                data_rows = 0
                for row in table:
                    if row and len(row) > 1:
                        date_str = str(row[1]).strip() if row[1] else ""
                        if date_str and date_str.count('-') == 2:
                            data_rows += 1
                
                print(f"  Table {t_idx+1}: {len(table)} rows, {data_rows} data rows")
                total_transactions += data_rows
    
    print(f"\n{'='*60}")
    print(f"TOTAL EXPECTED TRANSACTIONS: {total_transactions}")
    print(f"{'='*60}")