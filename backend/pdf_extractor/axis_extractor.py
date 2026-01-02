# backend/pdf_extractor/axis_extractor.py
import re
from .base_extractor import BasePDFExtractor


class AxisExtractor(BasePDFExtractor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.bank_name = "AXIS"

    def extract_metadata(self, text: str):
        account_match = re.search(r'Account\s+No\.\s*:\s*(\d+)', text, re.IGNORECASE)
        if account_match:
            self.account_number = account_match.group(1)

        name_match = re.search(r'(Ms\.|Mr\.|Mrs\.)\s+([A-Z\s]+)\s+Account', text)
        if name_match:
            self.account_holder = name_match.group(0).replace('Account', '').strip()

        self.statement_period = "Available in Statement"

    def extract_transactions(self, tables, text: str):
        """
        Extract AXIS transactions from text
        Format: DD/MM/YY DD/MM/YY Description - Debit Credit Balance
        """
        lines = text.split('\n')
        
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # Check if line starts with date pattern DD/MM/YY
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})', line)
            if not date_match:
                continue
            
            value_date = date_match.group(1)
            post_date = date_match.group(2)
            
            # Extract the rest of the line after dates
            remaining = line[date_match.end():].strip()
            
            # Check next few lines for complete transaction description
            description_parts = [remaining]
            j = i + 1
            while j < len(lines) and j < i + 5:
                next_line = lines[j].strip()
                # Stop if we hit another date or empty line
                if re.match(r'^\d{2}/\d{2}/\d{2}', next_line) or not next_line:
                    break
                # Check if line contains amount (ends with Cr or has balance)
                if re.search(r'[\d,]+\.\d{2}Cr$', next_line):
                    description_parts.append(next_line)
                    break
                description_parts.append(next_line)
                j += 1
            
            full_text = ' '.join(description_parts)
            
            # Extract amounts - looking for patterns like "268.65" or "62,541.51Cr"
            amounts = re.findall(r'[\d,]+\.\d{2}', full_text)
            
            if len(amounts) < 1:
                continue
            
            # Parse description and amounts
            # Remove amounts from description
            description = re.sub(r'[\d,]+\.\d{2}Cr?', '', full_text).strip()
            description = re.sub(r'\s+', ' ', description)
            
            # Determine debit/credit
            # Axis shows "Cr" suffix for balance and uses "TO TRF" for debit, "BY TRF" for credit
            is_credit = 'BY TRF' in description or 'SALARY' in description.upper() or 'REFUND' in description.upper()
            
            if len(amounts) == 1:
                # Only balance present
                balance = self.parse_amount(amounts[0])
                debit = 0.0
                credit = 0.0
            elif len(amounts) == 2:
                # Amount + Balance
                amount = self.parse_amount(amounts[0])
                balance = self.parse_amount(amounts[1])
                if is_credit:
                    debit = 0.0
                    credit = amount
                else:
                    debit = amount
                    credit = 0.0
            else:
                # Debit + Credit + Balance or other format
                balance = self.parse_amount(amounts[-1])
                if is_credit:
                    debit = 0.0
                    credit = self.parse_amount(amounts[0])
                else:
                    debit = self.parse_amount(amounts[0])
                    credit = 0.0
            
            transaction_type = "Credit" if is_credit or credit > 0 else "Debit"
            
            self.transactions.append({
                "date": value_date,
                "description": description,
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "transaction_type": transaction_type
            })

    def _is_valid_date(self, date_str: str) -> bool:
        date_patterns = [
            r'\d{2}/\d{2}/\d{2}',
            r'\d{2}-\d{2}-\d{2,4}',
        ]
        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False