# backend/pdf_extractor/base_extractor.py
import pdfplumber
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json


class BasePDFExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.bank_name = ""
        self.account_holder = ""
        self.account_number = ""
        self.statement_period = ""
        self.transactions = []

    def extract(self) -> Dict:
        with pdfplumber.open(self.pdf_path) as pdf:
            full_text = ""
            all_tables = []
            
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
            
            self.extract_metadata(full_text)
            self.extract_transactions(all_tables, full_text)
        
        return self.to_dict()

    def extract_metadata(self, text: str):
        raise NotImplementedError

    def extract_transactions(self, tables: List, text: str):
        raise NotImplementedError

    def parse_amount(self, value) -> float:
        if not value or value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        value = str(value).strip()
        value = re.sub(r'[^\d.,\-]', '', value)
        value = value.replace(',', '')
        if not value or value == '-':
            return 0.0
        try:
            return float(value)
        except:
            return 0.0

    def to_dict(self) -> Dict:
        return {
            "bank_name": self.bank_name,
            "account_holder": self.account_holder,
            "account_number": self.account_number,
            "statement_period": self.statement_period,
            "transactions": self.transactions
        }

    def save(self, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)