# backend/pdf_extractor/hdfc_extractor_debug.py
import re
from .base_extractor import BasePDFExtractor


class HDFCExtractor(BasePDFExtractor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.bank_name = "HDFC"

    def extract_metadata(self, text: str):
        """
        Extract account metadata from HDFC statement
        HDFC statements have various formats, so we try multiple patterns
        """
        # DEBUG: Print first 2000 characters to see what's available
        print("=" * 80)
        print("DEBUG: First 2000 characters of extracted text:")
        print("=" * 80)
        print(text[:2000])
        print("=" * 80)
        
        # Try multiple patterns for account number
        account_patterns = [
            r'Account\s+Number[:\s]+(\d+)',
            r'Account\s+No\.?[:\s]+(\d+)',
            r'A/c\s+No\.?[:\s]+(\d+)',
            r'Account[:\s]+(\d{10,})',
            r'Savings\s+Account[:\s]+(\d+)',
            r'(?:Account|A/C)\s*[:.]?\s*(\d{10,})',
            r'(\d{10,})',  # Last resort: any 10+ digit number
        ]
        
        for pattern in account_patterns:
            account_match = re.search(pattern, text, re.IGNORECASE)
            if account_match:
                self.account_number = account_match.group(1).strip()
                print(f"DEBUG: Found account number using pattern: {pattern}")
                print(f"DEBUG: Account Number: {self.account_number}")
                break
        
        if not self.account_number:
            print("DEBUG: No account number found!")
        
        # Try multiple patterns for account holder name
        name_patterns = [
            r'(?:Account\s+Holder|Customer\s+Name|Name)[:\s]+([A-Z][A-Z\s\.]{2,50})',
            r'(?:Dear|Mr\.|Ms\.|Mrs\.)\s+([A-Z][A-Z\s\.]{2,50})',
            r'Statement\s+for[:\s]+([A-Z][A-Z\s\.]{2,50})',
            r'(?:Name|Account\s+Name)[:\s]+([A-Z][A-Z\s\.]+)',
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
                # Filter out common non-name text
                if len(name) > 3 and not any(word in name.upper() for word in ['STATEMENT', 'ACCOUNT', 'BANK', 'BRANCH', 'ADDRESS']):
                    self.account_holder = name
                    print(f"DEBUG: Found account holder using pattern: {pattern}")
                    print(f"DEBUG: Account Holder: {self.account_holder}")
                    break
        
        if not self.account_holder:
            print("DEBUG: No account holder found!")
        
        # Try multiple patterns for statement period
        period_patterns = [
            r'Statement\s+Period[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
            r'Statement\s+from[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
            r'Period[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
            r'From[:\s]+([0-9/\-]+)[:\s]+To[:\s]+([0-9/\-]+)',
        ]
        
        for pattern in period_patterns:
            period_match = re.search(pattern, text, re.IGNORECASE)
            if period_match:
                if period_match.lastindex == 2:
                    # Pattern with separate From and To
                    self.statement_period = f"From {period_match.group(1)} To {period_match.group(2)}"
                else:
                    self.statement_period = period_match.group(1).strip()
                print(f"DEBUG: Found statement period using pattern: {pattern}")
                print(f"DEBUG: Statement Period: {self.statement_period}")
                break
        
        if not self.statement_period:
            print("DEBUG: No statement period found!")
        
        print("=" * 80)

    def extract_transactions(self, tables, text: str):
        for table in tables:
            if not table or len(table) < 2:
                continue

            header = [str(cell).lower().strip() if cell else '' for cell in table[0]]
            
            date_idx = self._find_column(header, ['date', 'transaction date', 'txn date'])
            desc_idx = self._find_column(header, ['description', 'narration', 'particulars', 'transaction details'])
            debit_idx = self._find_column(header, ['debit', 'withdrawal', 'withdraw', 'debit amount'])
            credit_idx = self._find_column(header, ['credit', 'deposit', 'credit amount'])
            balance_idx = self._find_column(header, ['balance', 'closing balance', 'available balance'])

            for row in table[1:]:
                if not row or len(row) < 2:
                    continue

                date_val = row[date_idx] if date_idx >= 0 and date_idx < len(row) else None
                if not date_val or not self._is_valid_date(str(date_val)):
                    continue

                description = row[desc_idx] if desc_idx >= 0 and desc_idx < len(row) else ""
                description = str(description).strip()
                
                # Skip empty or invalid descriptions
                if not description or description.lower() in ['', 'none', 'nan']:
                    continue

                debit = self.parse_amount(row[debit_idx]) if debit_idx >= 0 and debit_idx < len(row) else 0.0
                credit = self.parse_amount(row[credit_idx]) if credit_idx >= 0 and credit_idx < len(row) else 0.0
                balance = self.parse_amount(row[balance_idx]) if balance_idx >= 0 and balance_idx < len(row) else 0.0

                transaction_type = "Credit" if credit > 0 else "Debit"

                self.transactions.append({
                    "date": str(date_val).strip(),
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "transaction_type": transaction_type
                })
        
        # If still empty after transactions, try to infer from transaction dates
        if not self.statement_period and self.transactions:
            try:
                dates = [t['date'] for t in self.transactions if 'date' in t]
                if dates:
                    self.statement_period = f"From {dates[-1]} To {dates[0]}"
                    print(f"DEBUG: Inferred statement period from transactions: {self.statement_period}")
            except Exception as e:
                print(f"DEBUG: Error inferring statement period: {e}")

    def _find_column(self, header, keywords):
        """Find column index by matching keywords"""
        for idx, col in enumerate(header):
            for keyword in keywords:
                if keyword in col:
                    return idx
        return -1  # Return -1 if not found

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string matches date patterns"""
        date_patterns = [
            r'\d{2}/\d{2}/\d{2,4}',
            r'\d{2}-\d{2}-\d{2,4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}',  # 01 Jan 2024
        ]
        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False