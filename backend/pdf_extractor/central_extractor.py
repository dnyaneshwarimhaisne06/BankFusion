# backend/pdf_extractor/central_extractor.py
import re
from .base_extractor import BasePDFExtractor


class CentralExtractor(BasePDFExtractor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.bank_name = "CENTRAL"

    def extract_metadata(self, text: str):
        account_match = re.search(r'Account\s+No\.\s*:\s*(\d+)', text, re.IGNORECASE)
        if account_match:
            self.account_number = account_match.group(1)

        name_match = re.search(r'(Mr\.|Ms\.|Mrs\.)\s+([A-Z\s]+)\s+Account', text)
        if name_match:
            self.account_holder = f"{name_match.group(1)} {name_match.group(2).strip()}"

        self.statement_period = "Available in Statement"

    def extract_transactions(self, tables, text: str):
        """
        Central Bank transactions are text-based, not in clean tables.
        Format: DD/MM/YY DD/MM/YY Description - Amount Amount BalanceCr
        Example: 25/10/25 25/10/25 TO TRF. - 1,813.63 335,281.72Cr
        """
        # First try table extraction
        table_count = self._extract_from_tables(tables)
        
        # If no transactions found from tables, use text extraction
        if table_count == 0:
            print(f"      WARNING: No tables found, using text extraction...")
            self._extract_from_text(text)

    def _extract_from_tables(self, tables):
        """Try to extract from tables first"""
        count = 0
        for table in tables:
            if not table or len(table) < 2:
                continue

            for row in table:
                if not row or len(row) < 4:
                    continue
                
                date_str = str(row[0]).strip() if row[0] else ""
                if not self._is_valid_date(date_str):
                    continue
                
                if 'brought forward' in date_str.lower() or 'carried forward' in date_str.lower():
                    continue
                
                description = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                if not description or 'details' in description.lower():
                    continue
                
                debit = self.parse_amount(row[4]) if len(row) > 4 else 0.0
                credit = self.parse_amount(row[5]) if len(row) > 5 else 0.0
                balance = self.parse_amount(row[6]) if len(row) > 6 else 0.0
                
                if debit == 0.0 and credit == 0.0:
                    continue
                
                transaction_type = "Credit" if credit > 0 or 'BY TRF' in description or 'SALARY' in description.upper() else "Debit"
                
                self.transactions.append({
                    "date": date_str,
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                    "transaction_type": transaction_type
                })
                count += 1
        
        return count

    def _extract_from_text(self, text: str):
        """
        Extract transactions directly from text
        Central Bank format: Date Date Description ... Amounts
        """
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for lines starting with date pattern DD/MM/YY
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+(.+)', line)
            if not date_match:
                i += 1
                continue
            
            value_date = date_match.group(1)
            post_date = date_match.group(2)
            remaining_text = date_match.group(3).strip()
            
            # Skip summary rows
            if 'BROUGHT FORWARD' in remaining_text or 'CARRIED FORWARD' in remaining_text:
                i += 1
                continue
            
            # Collect the full transaction (may span multiple lines)
            transaction_lines = [remaining_text]
            
            # Look ahead for continuation lines (lines that don't start with date)
            j = i + 1
            while j < len(lines) and j < i + 10:  # Max 10 lines ahead
                next_line = lines[j].strip()
                # Stop if we hit another date or empty line or page marker
                if not next_line or re.match(r'^\d{2}/\d{2}/\d{2}', next_line):
                    break
                if 'Central Bank' in next_line or 'STATEMENT OF ACCOUNT' in next_line:
                    break
                if 'Page No.' in next_line or 'Value Post Details' in next_line:
                    break
                
                transaction_lines.append(next_line)
                j += 1
            
            # Move index forward
            i = j
            
            # Join all lines with space
            transaction_text = ' '.join(transaction_lines)
            
            # Remove 'Cr' suffix from balance
            transaction_text = transaction_text.replace('Cr', '')
            
            # Find all numbers (amounts) in the transaction text
            amounts = re.findall(r'[\d,]+\.\d{2}', transaction_text)
            
            if len(amounts) < 2:
                continue
            
            # Extract description by removing all amount patterns from the end
            # Work backwards to remove amounts from the description
            description = transaction_text
            for amount in reversed(amounts):
                # Remove the last occurrence of this amount
                last_pos = description.rfind(amount)
                if last_pos != -1:
                    description = description[:last_pos] + description[last_pos + len(amount):]
            
            # Clean description - remove extra spaces, dashes, dots
            description = re.sub(r'\s+', ' ', description)  # Multiple spaces to single
            description = re.sub(r'\s*-\s*$', '', description)  # Remove trailing dash
            description = re.sub(r'\s*\.\s*$', '', description)  # Remove trailing dot
            description = description.strip()
            
            # Replace spaces around dots with just the dot for better formatting
            description = re.sub(r'\s*\.\s*', '.', description)
            
            # Last amount is always balance
            balance = self.parse_amount(amounts[-1])
            
            # Determine debit/credit
            debit = 0.0
            credit = 0.0
            
            if len(amounts) == 2:
                # Format: Amount Balance
                amount = self.parse_amount(amounts[0])
                # Check if credit transaction
                if 'BY TRF' in description or 'SALARY' in description.upper() or 'REFUND' in description.upper() or 'TRF FROM' in description:
                    credit = amount
                else:
                    debit = amount
            elif len(amounts) >= 3:
                # Format: Debit Credit Balance or multiple amounts
                # Second-to-last is typically the transaction amount
                amount = self.parse_amount(amounts[-2])
                if 'BY TRF' in description or 'SALARY' in description.upper() or 'REFUND' in description.upper():
                    credit = amount
                else:
                    debit = amount
            
            if debit == 0.0 and credit == 0.0:
                continue
            
            transaction_type = "Credit" if credit > 0 else "Debit"
            
            self.transactions.append({
                "date": value_date,
                "description": description,
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "transaction_type": transaction_type
            })

    def _is_valid_date(self, date_str: str) -> bool:
        return bool(re.match(r'\d{2}/\d{2}/\d{2}', date_str.strip()))