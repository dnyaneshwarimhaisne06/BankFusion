# backend/pdf_extractor/boi_extractor.py
import re
from .base_extractor import BasePDFExtractor


class BOIExtractor(BasePDFExtractor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.bank_name = "BOI"

    def extract_metadata(self, text: str):
        # Account Number
        account_match = re.search(r'Account\s+No\s*:\s*(\d+)', text, re.IGNORECASE)
        if account_match:
            self.account_number = account_match.group(1)

        # Account Holder Name
        name_match = re.search(r'Name\s*:\s*(.+)', text, re.IGNORECASE)
        if name_match:
            name_line = name_match.group(1).strip()
            self.account_holder = name_line.split('\n')[0].strip()

        # Statement Period
        period_match = re.search(r'period\s+(.+?\d{4}\s+to\s+.+?\d{4})', text, re.IGNORECASE)
        if period_match:
            self.statement_period = period_match.group(1).strip()

    def extract_transactions(self, tables, text: str):
        """
        Extract BOI transactions from ALL tables across ALL pages
        BOI statements have tables on every page with the same structure
        """
        transaction_count = 0
        
        for table in tables:
            if not table or len(table) < 2:
                continue

            # Check if this is a transaction table
            # BOI tables either have header or start directly with data
            first_row = table[0]
            first_row_text = ' '.join([str(cell).lower() if cell else '' for cell in first_row])
            
            # Determine if first row is header or data
            is_header = 'txn date' in first_row_text or 'withdrawal' in first_row_text or 'sl no' in first_row_text
            
            # Start processing from correct row
            start_idx = 1 if is_header else 0
            
            # Process each row
            for row in table[start_idx:]:
                if not row or len(row) < 6:
                    continue
                
                # BOI table structure: [Sl No, Txn Date, Description, Cheque No, Withdrawal, Deposits, Balance]
                # Indices: 0, 1, 2, 3, 4, 5, 6
                
                # Get serial number (optional - for validation)
                serial = str(row[0]).strip() if row[0] else ""
                
                # Get date (MUST BE PRESENT)
                date_str = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                if not date_str or not self._is_valid_date(date_str):
                    continue
                
                # Get description (MUST BE PRESENT)
                description = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                if not description or description == 'None' or description == '':
                    continue
                
                # Skip footer/summary rows
                if 'statement generated' in description.lower() or 'page summary' in description.lower():
                    continue
                
                # Get withdrawal amount (column 4)
                withdrawal_val = row[4] if len(row) > 4 and row[4] else ""
                withdrawal = self.parse_amount(withdrawal_val)
                
                # Get deposit amount (column 5)
                deposit_val = row[5] if len(row) > 5 and row[5] else ""
                deposit = self.parse_amount(deposit_val)
                
                # Get balance (column 6)
                balance_val = row[6] if len(row) > 6 and row[6] else ""
                balance = self.parse_amount(balance_val)
                
                # Skip if no transaction (both withdrawal and deposit are 0)
                if withdrawal == 0.0 and deposit == 0.0:
                    continue
                
                # Determine transaction type
                if deposit > 0:
                    transaction_type = "Credit"
                    debit = 0.0
                    credit = deposit
                else:
                    transaction_type = "Debit"
                    debit = withdrawal
                    credit = 0.0
                
                self.transactions.append({
                    "date": date_str,
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "transaction_type": transaction_type
                })
                
                transaction_count += 1
        
        print(f"      DEBUG: Extracted {transaction_count} transactions from {len(tables)} tables")

    def _is_valid_date(self, date_str: str) -> bool:
        """Validate BOI date format: DD-MM-YYYY"""
        return bool(re.match(r'\d{2}-\d{2}-\d{4}', date_str.strip()))