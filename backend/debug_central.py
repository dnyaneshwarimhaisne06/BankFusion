# backend/debug_central_detailed.py
import pdfplumber
from pathlib import Path
import re

project_root = Path(__file__).parent.parent
pdf_path = project_root / "data" / "raw_pdfs" / "central" / "Statement_03_300txn.pdf"

print("=" * 80)
print("DETAILED CENTRAL BANK DEBUG")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    
    # Check first 3 pages
    for page_num in range(min(3, len(pdf.pages))):
        page = pdf.pages[page_num]
        print(f"\n{'='*80}")
        print(f"PAGE {page_num + 1}")
        print(f"{'='*80}")
        
        # Extract text
        text = page.extract_text()
        lines = text.split('\n')
        
        print("\n--- TEXT EXTRACTION (First 25 lines) ---")
        for i, line in enumerate(lines[:25], 1):
            print(f"{i:3}. {line}")
        
        # Extract tables
        tables = page.extract_tables()
        print(f"\n--- TABLE EXTRACTION ---")
        print(f"Number of tables found: {len(tables)}")
        
        if tables:
            for t_idx, table in enumerate(tables):
                print(f"\n  Table {t_idx + 1}:")
                print(f"    Total rows: {len(table)}")
                if table:
                    print(f"    Total columns: {len(table[0]) if table else 0}")
                    print("\n    First 10 rows:")
                    for r_idx, row in enumerate(table[:10]):
                        print(f"    Row {r_idx}: {row}")
        else:
            print("  NO TABLES FOUND - This is the problem!")
            print("\n  Trying alternative table settings...")
            
            # Try with different table settings
            tables_alt = page.extract_tables(table_settings={
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
            })
            print(f"  Alternative method found {len(tables_alt)} tables")
            
            if not tables_alt:
                print("\n  Tables still not found. Trying text-based extraction...")
                print("\n  Looking for date patterns (DD/MM/YY):")
                date_pattern = r'\d{2}/\d{2}/\d{2}'
                date_lines = [line for line in lines if re.search(date_pattern, line)]
                print(f"  Found {len(date_lines)} lines with dates")
                if date_lines:
                    print("\n  First 5 date lines:")
                    for line in date_lines[:5]:
                        print(f"    {line}")