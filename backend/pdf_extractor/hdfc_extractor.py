# backend/pdf_extractor/hdfc_extractor.py
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
        # Extract account number - try multiple patterns
        account_patterns = [
            r'Account\s+Number[:\s]+(\d+)',
            r'Account\s+No\.?[:\s]+(\d+)',
            r'A/c\s+No\.?[:\s]+(\d+)',
            r'Account[:\s]+(\d{10,})',
            r'Savings\s+Account[:\s]+(\d+)',
            r'(?:Account|A/C)\s*[:.]?\s*(\d{10,})',
        ]
        
        for pattern in account_patterns:
            account_match = re.search(pattern, text, re.IGNORECASE)
            if account_match:
                self.account_number = account_match.group(1).strip()
                break
        
        # Extract account holder name - HDFC specific patterns
        # Try to find name near account number or in common HDFC locations
        name_patterns = [
            # Pattern 1: Name after "Customer Name", "Account Holder", etc
            r'(?:Customer\s+Name|Account\s+Holder|Name\s+of\s+Account\s+Holder|Account\s+Name)[:\s]+([A-Z][A-Z\s\.&]{2,50})(?:\s+Account|\s+Address|\s+Branch|\s+IFSC|\s*\n|$)',
            
            # Pattern 2: Name at the start of address block
            r'^([A-Z][A-Z\s\.&]{2,50})\s+(?:Address|Home|Office|Branch)',
            
            # Pattern 3: Name before Account Number
            r'([A-Z][A-Z\s\.&]{2,50})\s+Account\s+(?:Number|No)',
            
            # Pattern 4: "Dear" salutation
            r'Dear\s+(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][A-Z\s\.&]{2,50})',
            r'Dear\s+([A-Z][A-Z\s\.&]{2,50})',
            
            # Pattern 5: Name on separate line before account details
            r'\n([A-Z][A-Z\s\.&]{2,50})\s*\n.*?(?:Account|Statement|Branch)',
            
            # Pattern 6: Name in standard HDFC header format
            r'(?:Statement\s+for|Statement\s+of)[:\s]+([A-Z][A-Z\s\.&]{2,50})',
            
            # Pattern 7: Simple capitalized name near start (last resort)
            r'^.*?\b([A-Z][A-Z\s\.]{10,50})\b',
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip()
                
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)  # Multiple spaces to single
                name = name.strip()
                
                # Filter out common non-name text
                excluded_words = [
                    'STATEMENT', 'ACCOUNT', 'BANK', 'BRANCH', 'ADDRESS', 'SAVINGS',
                    'CURRENT', 'DEPOSIT', 'INDIA', 'LIMITED', 'DETAILS', 'PERIOD',
                    'BALANCE', 'CREDIT', 'DEBIT', 'TRANSACTION', 'DATE', 'DESCRIPTION',
                    'AMOUNT', 'IFSC', 'MICR', 'CODE', 'CUSTOMER', 'HOLDER', 'NUMBER',
                    'MOBILE', 'EMAIL', 'PHONE', 'CITY', 'STATE', 'PINCODE', 'COUNTRY'
                ]
                
                name_upper = name.upper()
                is_valid_name = True
                
                # Check if name contains excluded words
                for excluded in excluded_words:
                    if excluded in name_upper:
                        is_valid_name = False
                        break
                
                # Additional validation: name should have at least 2 parts
                name_parts = name.split()
                if len(name_parts) < 2:
                    is_valid_name = False
                
                # Additional validation: name should not be too long
                if len(name) > 50:
                    is_valid_name = False
                
                # Additional validation: name should not contain numbers
                if re.search(r'\d', name):
                    is_valid_name = False
                
                if is_valid_name and len(name) > 3:
                    self.account_holder = name
                    break
        
        # If still no name found, try extracting from first 500 chars more aggressively
        if not self.account_holder:
            first_part = text[:500]
            lines = first_part.split('\n')
            for line in lines:
                line = line.strip()
                # Look for lines with only capital letters and spaces (typical name format)
                if re.match(r'^[A-Z][A-Z\s\.&]{10,50}$', line):
                    name = line.strip()
                    # Validate it's not a header
                    if not any(word in name for word in ['STATEMENT', 'BANK', 'ACCOUNT', 'HDFC']):
                        self.account_holder = name
                        break
        
        # Extract statement period - try multiple patterns
        period_patterns = [
            r'Statement\s+Period[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
            r'Statement\s+from[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
            r'Period[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
            r'From[:\s]+([0-9/\-]+)[:\s]+To[:\s]+([0-9/\-]+)',
            r'Statement\s+for\s+the\s+period[:\s]+([0-9/\-\s]+(?:to|To|TO)[0-9/\-\s]+)',
        ]
        
        for pattern in period_patterns:
            period_match = re.search(pattern, text, re.IGNORECASE)
            if period_match:
                if period_match.lastindex == 2:
                    # Pattern with separate From and To
                    self.statement_period = f"From {period_match.group(1)} To {period_match.group(2)}"
                else:
                    self.statement_period = period_match.group(1).strip()
                break
        
        # If still empty, try to extract from date range in transactions
        if not self.statement_period and self.transactions:
            try:
                dates = [t['date'] for t in self.transactions if 'date' in t]
                if dates:
                    self.statement_period = f"{dates[-1]} To {dates[0]}"
            except:
                pass

    def extract_transactions(self, tables, text: str):
        for table in tables:
            if not table or len(table) < 2:
                continue

            header = [str(cell).lower().strip() if cell else '' for cell in table[0]]
            
            date_idx = self._find_column(header, ['date', 'transaction date', 'txn date', 'value date'])
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