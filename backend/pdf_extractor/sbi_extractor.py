# backend/pdf_extractor/sbi_extractor.py
import re
from datetime import datetime
from .base_extractor import BasePDFExtractor


class SBIExtractor(BasePDFExtractor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.bank_name = "SBI"

    def extract_metadata(self, text: str):
        account_match = re.search(r'Account\s+Number\s+(\d+)', text, re.IGNORECASE)
        if account_match:
            self.account_number = account_match.group(1)

        name_match = re.search(r'Account\s+Name\s+(.+)', text, re.IGNORECASE)
        if name_match:
            name_line = name_match.group(1).strip()
            self.account_holder = name_line.split('\n')[0].strip()

        period_match = re.search(r'Account\s+Statement\s+for\s+the\s+period\s+(.+)', text, re.IGNORECASE)
        if period_match:
            self.statement_period = period_match.group(1).strip()

    def extract_transactions(self, tables, text: str):
        """
        Extract transactions directly from text using regex patterns
        SBI format: Date Narration RefNo Debit Credit Balance
        """
        # Pattern to match SBI transaction lines
        # Example: 23-Nov-25 UPI-BIGBASKET-7150 592270 3,124.00 87,457.00
        pattern = r'(\d{2}-[A-Za-z]{3}-\d{2})\s*\([\d-]+\)\s*(.+?)\s+(\d+)\s+([\d,]+\.\d{2})?\s*([\d,]+\.\d{2})?\s+([\d,]+\.\d{2})'
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Try to match the pattern
            match = re.search(pattern, line)
            if match:
                date_str = match.group(1)
                description = match.group(2).strip()
                ref_no = match.group(3)
                debit_str = match.group(4) if match.group(4) else "0.00"
                credit_str = match.group(5) if match.group(5) else "0.00"
                balance_str = match.group(6)
                
                # Skip header rows
                if 'Narration' in description or 'Date' in description:
                    continue
                
                debit = self.parse_amount(debit_str)
                credit = self.parse_amount(credit_str)
                balance = self.parse_amount(balance_str)
                
                # Determine transaction type
                transaction_type = "Credit" if credit > 0 else "Debit"
                
                self.transactions.append({
                    "date": date_str,
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "transaction_type": transaction_type
                })

        # Fallback to table extraction if text parsing fails
        if len(self.transactions) == 0:
            self._extract_from_tables(tables)

    def _extract_from_tables(self, tables):
        """Fallback table-based extraction"""
        for table in tables:
            if not table or len(table) < 2:
                continue

            for row in table:
                if not row or len(row) < 4:
                    continue
                
                # Check if first column looks like a date
                date_val = str(row[0]).strip() if row[0] else ""
                if not self._is_valid_date(date_val):
                    continue
                
                # Extract data from row
                description = str(row[1]).strip() if len(row) > 1 else ""
                
                # Skip headers
                if 'Narration' in description or 'Date' in date_val:
                    continue
                
                # Find numeric columns (debit, credit, balance)
                numeric_values = []
                for cell in row[2:]:
                    val = self.parse_amount(cell)
                    if val > 0:
                        numeric_values.append(val)
                
                if len(numeric_values) < 2:
                    continue
                
                # Last value is always balance
                balance = numeric_values[-1]
                
                # Determine debit/credit
                if len(numeric_values) == 2:
                    # Only one amount + balance
                    amount = numeric_values[0]
                    # Check description for credit indicators
                    if any(word in description.upper() for word in ['SALARY', 'CREDIT', 'NEFT CR', 'IMPS CR', 'RTGS']):
                        debit = 0.0
                        credit = amount
                    else:
                        debit = amount
                        credit = 0.0
                else:
                    # Both debit and credit present
                    debit = numeric_values[0] if numeric_values[0] != balance else 0.0
                    credit = numeric_values[1] if len(numeric_values) > 2 and numeric_values[1] != balance else 0.0
                
                transaction_type = "Credit" if credit > 0 else "Debit"
                
                self.transactions.append({
                    "date": date_val,
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "transaction_type": transaction_type
                })

    def _is_valid_date(self, date_str: str) -> bool:
        date_patterns = [
            r'\d{2}-[A-Za-z]{3}-\d{2}',
            r'\d{2}/\d{2}/\d{2,4}',
            r'\d{2}-\d{2}-\d{2,4}',
        ]
        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False