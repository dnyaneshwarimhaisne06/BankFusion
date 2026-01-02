# backend/pdf_extractor/union_extractor.py
import re
from .base_extractor import BasePDFExtractor


class UnionExtractor(BasePDFExtractor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.bank_name = "UNION"

    def extract_metadata(self, text: str):
        account_match = re.search(r'Account\s+(?:No|Number)[:\s]+(\d+)', text, re.IGNORECASE)
        if account_match:
            self.account_number = account_match.group(1)

        name_match = re.search(r'(?:Name|Account\s+Holder)[:\s]+([A-Z\s]+)', text, re.IGNORECASE)
        if name_match:
            self.account_holder = name_match.group(1).strip()

        period_match = re.search(r'Statement\s+Period[:\s]+(.+)', text, re.IGNORECASE)
        if period_match:
            self.statement_period = period_match.group(1).strip()

    def extract_transactions(self, tables, text: str):
        for table in tables:
            if not table or len(table) < 2:
                continue

            header = [str(cell).lower().strip() if cell else '' for cell in table[0]]
            
            # Find column indices
            tran_id_idx = self._find_column(header, ['tran id', 'transaction id', 'tranid'])
            date_idx = self._find_column(header, ['tran date', 'date', 'transaction date'])
            desc_idx = self._find_column(header, ['remarks', 'description', 'particulars', 'narration'])
            amount_idx = self._find_column(header, ['amount', 'amount (rs.)', 'amount (rs)'])
            balance_idx = self._find_column(header, ['balance', 'balance (rs.)', 'balance (rs)'])

            for row in table[1:]:
                if not row or len(row) < 2:
                    continue

                # Extract transaction ID
                transaction_id = ""
                if tran_id_idx >= 0 and tran_id_idx < len(row) and row[tran_id_idx]:
                    transaction_id = str(row[tran_id_idx]).strip()
                
                # Extract date
                date_val = row[date_idx] if date_idx >= 0 and date_idx < len(row) else None
                if not date_val or not self._is_valid_date(str(date_val)):
                    continue

                # Extract description from Remarks column
                description = ""
                if desc_idx >= 0 and desc_idx < len(row) and row[desc_idx]:
                    description = str(row[desc_idx]).strip()
                
                # Skip empty descriptions
                if not description or description.lower() in ['', 'none', 'nan']:
                    continue

                # Extract amount and determine debit/credit
                debit = 0.0
                credit = 0.0
                
                if amount_idx >= 0 and amount_idx < len(row) and row[amount_idx]:
                    amount_str = str(row[amount_idx]).strip()
                    
                    # Check if it's debit or credit based on (Dr) or (Cr) suffix
                    if '(Dr)' in amount_str or '(dr)' in amount_str:
                        debit = self.parse_amount(amount_str.replace('(Dr)', '').replace('(dr)', ''))
                    elif '(Cr)' in amount_str or '(cr)' in amount_str:
                        credit = self.parse_amount(amount_str.replace('(Cr)', '').replace('(cr)', ''))
                    else:
                        # If no suffix, try to determine from balance change or assume debit
                        amount = self.parse_amount(amount_str)
                        # Default to debit if we can't determine
                        debit = amount

                # Extract balance
                balance = 0.0
                if balance_idx >= 0 and balance_idx < len(row) and row[balance_idx]:
                    balance_str = str(row[balance_idx]).strip()
                    # Remove any (Cr) or (Dr) suffix from balance
                    balance_str = balance_str.replace('(Cr)', '').replace('(cr)', '').replace('(Dr)', '').replace('(dr)', '')
                    balance = self.parse_amount(balance_str)

                # Determine transaction type
                transaction_type = "Credit" if credit > 0 else "Debit"

                self.transactions.append({
                    # "transaction_id": transaction_id,
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
            r'\d{4}-\d{2}-\d{2}'
        ]
        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False