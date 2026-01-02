# backend/normalizer/transaction_normalizer.py
import re
from datetime import datetime
from typing import Dict, List


class TransactionNormalizer:
    DEBIT_KEYWORDS = ['debit', 'withdraw', 'withdrawal', 'dr', 'pos', 'atm', 'payment']
    CREDIT_KEYWORDS = ['credit', 'deposit', 'cr', 'neft in', 'imps in', 'salary', 'transfer in']

    @staticmethod
    def normalize_date(date_str: str) -> str:
        date_formats = [
            '%d/%m/%y', '%d/%m/%Y',
            '%d-%m-%y', '%d-%m-%Y',
            '%Y-%m-%d', '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 2000)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        
        return date_str

    @staticmethod
    def normalize_transaction_type(transaction_type: str, description: str, debit: float, credit: float) -> str:
        if credit > 0:
            return "CREDIT"
        if debit > 0:
            return "DEBIT"
        
        transaction_type_lower = transaction_type.lower()
        description_lower = description.lower()
        
        for keyword in TransactionNormalizer.CREDIT_KEYWORDS:
            if keyword in transaction_type_lower or keyword in description_lower:
                return "CREDIT"
        
        for keyword in TransactionNormalizer.DEBIT_KEYWORDS:
            if keyword in transaction_type_lower or keyword in description_lower:
                return "DEBIT"
        
        return "DEBIT"

    @staticmethod
    def normalize_bank_name(bank_name: str) -> str:
        bank_mapping = {
            'hdfc': 'HDFC',
            'axis': 'AXIS',
            'sbi': 'SBI',
            'union': 'UNION',
            'boi': 'BOI',
            'bank of india': 'BOI',
            'central': 'CENTRAL'
        }
        return bank_mapping.get(bank_name.lower(), bank_name.upper())

    @staticmethod
    def normalize_transaction(transaction: Dict, bank_name: str, account_number: str) -> Dict:
        debit = transaction.get('debit', 0.0)
        credit = transaction.get('credit', 0.0)
        
        amount = credit if credit > 0 else debit
        
        transaction_type = TransactionNormalizer.normalize_transaction_type(
            transaction.get('transaction_type', ''),
            transaction.get('description', ''),
            debit,
            credit
        )
        
        normalized = {
            "transaction_date": TransactionNormalizer.normalize_date(transaction.get('date', '')),
            "description": transaction.get('description', '').strip(),
            "amount": amount,
            "transaction_type": transaction_type,
            "bank_name": TransactionNormalizer.normalize_bank_name(bank_name),
            "account_number": account_number,
            "balance": transaction.get('balance', 0.0)
        }
        
        return normalized

    @staticmethod
    def normalize_statement(statement_data: Dict) -> List[Dict]:
        normalized_transactions = []
        
        bank_name = statement_data.get('bank_name', '')
        account_number = statement_data.get('account_number', '')
        transactions = statement_data.get('transactions', [])
        
        for transaction in transactions:
            normalized = TransactionNormalizer.normalize_transaction(
                transaction,
                bank_name,
                account_number
            )
            normalized_transactions.append(normalized)
        
        return normalized_transactions