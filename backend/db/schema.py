"""
MongoDB Schema for Bank Statements (Polymorphic Parent + Normalized Transactions)
Two Collections: bank_statements (parent) + bank_transactions (normalized)
"""

from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId

# Bank type constants
BANK_TYPES = {
    'SBI': 'SBI',
    'HDFC': 'HDFC',
    'BOI': 'BOI',
    'CBI': 'CBI',  # Central Bank of India
    'UNION': 'UNION',
    'AXIS': 'AXIS'
}

# Channel mapping
CHANNEL_MAP = {
    'UPI': 'UPI',
    'CARD': 'CARD',
    'POS': 'CARD',
    'ATM': 'ATM',
    'IMPS': 'BANK_TRANSFER',
    'NEFT': 'BANK_TRANSFER',
    'RTGS': 'BANK_TRANSFER',
    'CHEQUE': 'BANK_TRANSFER',
    'ONLINE': 'BANK_TRANSFER',
    'OTHER': 'BANK_TRANSFER'
}

# Category mapping (no "Unknown" or "others")
CATEGORY_MAP = {
    'food_dining': 'food_dining',
    'shopping': 'shopping',
    'entertainment': 'entertainment',
    'bills_utilities': 'bills_utilities',
    'transport': 'transport',
    'healthcare': 'healthcare',
    'education': 'education',
    'insurance': 'insurance',
    'emi_loan': 'emi_loan',
    'income': 'income',
    'transfer': 'transfer',
    'cash_withdrawal': 'cash',
    'cash': 'cash',
    'investment': 'investment',
    'travel': 'travel',
    'fuel': 'fuel',
    'petrol': 'fuel',
    'groceries': 'groceries'
}

def normalize_date(date_str: Any) -> datetime:
    """Convert date string to ISODate"""
    if isinstance(date_str, datetime):
        return date_str
    
    if not date_str or str(date_str).strip() in ['', 'None', 'null']:
        return datetime.now()
    
    date_str = str(date_str).strip()
    
    # Common date formats
    formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
        '%d/%m/%y', '%d-%m-%y', '%y-%m-%d',
        '%d/%m/%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S',
        '%d-%b-%y', '%d-%b-%Y', '%d/%b/%y', '%d/%b/%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.split('\n')[0].split('(')[0].strip(), fmt)
        except:
            continue
    
    # Fallback to current date
    return datetime.now()

def normalize_direction(debit: float, credit: float, transaction_type: str) -> str:
    """Convert DEBIT/CREDIT to debit/credit"""
    if debit and debit > 0:
        return 'debit'
    elif credit and credit > 0:
        return 'credit'
    elif transaction_type:
        txn_type = str(transaction_type).upper()
        if 'DEBIT' in txn_type or 'DR' in txn_type or 'WITHDRAW' in txn_type:
            return 'debit'
        elif 'CREDIT' in txn_type or 'CR' in txn_type or 'DEPOSIT' in txn_type:
            return 'credit'
    return 'debit'  # Default

def normalize_channel(channel: str, description: str) -> str:
    """Detect channel: UPI / CARD / ATM / BANK_TRANSFER"""
    if not channel:
        channel = ''
    if not description:
        description = ''
    
    text = (str(channel) + ' ' + str(description)).upper()
    
    if 'UPI' in text or 'RRN' in text:
        return 'UPI'
    elif 'POS' in text or 'CARD' in text:
        return 'CARD'
    elif 'ATM' in text or 'ATW' in text:
        return 'ATM'
    elif 'IMPS' in text or 'NEFT' in text or 'RTGS' in text:
        return 'BANK_TRANSFER'
    elif 'CHEQUE' in text:
        return 'BANK_TRANSFER'
    else:
        return 'BANK_TRANSFER'  # Default

def normalize_merchant(merchant: str, description: str) -> str:
    """Extract real merchant (remove IDs/numbers)"""
    if merchant and merchant.strip() and merchant.upper() not in ['UNKNOWN', 'NONE', 'NULL', '']:
        # Remove common patterns
        merchant = str(merchant).strip()
        # Remove card numbers, IDs
        import re
        merchant = re.sub(r'\d{4,}', '', merchant)  # Remove 4+ digit numbers
        merchant = re.sub(r'XXXXXX', '', merchant)
        merchant = re.sub(r'POS\s*', '', merchant, flags=re.IGNORECASE)
        merchant = merchant.strip()
        if merchant:
            return merchant
    
    # Try to extract from description
    if description:
        desc = str(description).upper()
        # Common merchant patterns
        merchants = ['SWIGGY', 'ZOMATO', 'AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 
                     'NETFLIX', 'SPOTIFY', 'PAYTM', 'PHONEPE', 'GOOGLEPAY', 'BHIM',
                     'UBER', 'OLA', 'RAPIDO', 'BIG BAZAAR', 'DMART', 'RELIANCE',
                     'BARBEQUE NATION', 'MCDONALDS', 'KFC', 'DOMINOS', 'PIZZA HUT']
        
        for m in merchants:
            if m in desc:
                return m.replace('_', ' ').title()
    
    return 'General'  # Never use Unknown

def normalize_category(category: str, merchant: str, description: str) -> str:
    """Assign category by merchant/intent (no Unknown or others)"""
    if category and category.strip() and category.lower() not in ['unknown', 'others', 'other', 'none']:
        cat = category.lower().strip()
        if cat in CATEGORY_MAP:
            return CATEGORY_MAP[cat]
        return cat
    
    # Infer from merchant
    merchant_upper = str(merchant).upper()
    desc_upper = str(description).upper() if description else ''
    text = merchant_upper + ' ' + desc_upper
    
    # Food
    if any(x in text for x in ['SWIGGY', 'ZOMATO', 'FOOD', 'RESTAURANT', 'MCDONALDS', 'KFC', 'DOMINOS', 'PIZZA']):
        return 'food_dining'
    # Shopping
    elif any(x in text for x in ['AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'SHOPPING', 'PURCHASE']):
        return 'shopping'
    # Entertainment
    elif any(x in text for x in ['NETFLIX', 'SPOTIFY', 'MOVIE', 'ENTERTAINMENT']):
        return 'entertainment'
    # Transport
    elif any(x in text for x in ['UBER', 'OLA', 'RAPIDO', 'CAB', 'TAXI', 'TRANSPORT']):
        return 'transport'
    # Fuel
    elif any(x in text for x in ['PETROL', 'FUEL', 'GAS', 'BPCL', 'HP', 'IOCL']):
        return 'fuel'
    # Bills
    elif any(x in text for x in ['BILL', 'ELECTRICITY', 'WATER', 'PHONE', 'INTERNET', 'DTH', 'RECHARGE']):
        return 'bills_utilities'
    # Income
    elif any(x in text for x in ['SALARY', 'CREDIT', 'DEPOSIT', 'INTEREST']):
        return 'income'
    # Cash
    elif any(x in text for x in ['ATM', 'CASH', 'WITHDRAW']):
        return 'cash'
    # Transfer
    elif any(x in text for x in ['TRANSFER', 'IMPS', 'NEFT', 'RTGS']):
        return 'transfer'
    # Default
    else:
        return 'transfer'  # Default fallback (not "others")

def create_bank_statement_doc(bank_type: str, account_data: Dict, metadata: Dict, bank_specific: Optional[Dict] = None) -> Dict:
    """Create bank_statements document (polymorphic parent)"""
    bank_code = BANK_TYPES.get(bank_type.upper(), bank_type.upper())
    
    doc = {
        'bankType': bank_code,
        'accountNumber': account_data.get('account_number'),
        'accountHolder': account_data.get('account_holder'),
        'branch': account_data.get('branch'),
        'ifsc': account_data.get('ifsc'),
        'statementPeriod': account_data.get('statement_period'),
        'generatedAt': normalize_date(metadata.get('generated_at')),
        'totalTransactions': metadata.get('total_transactions', 0),
        'normalizationMethod': metadata.get('normalization_method', 'hybrid'),
        'createdAt': datetime.now()
    }
    
    # Add bank-specific fields
    if bank_specific:
        doc[f'bankSpecific.{bank_code}'] = bank_specific
    
    return doc

def create_transaction_doc(statement_id: ObjectId, bank_type: str, original: Dict, normalized: Dict) -> Dict:
    """Create bank_transactions document (normalized)"""
    bank_code = BANK_TYPES.get(bank_type.upper(), bank_type.upper())
    
    # Extract data
    date = normalize_date(original.get('date'))
    debit = float(original.get('debit', 0) or 0)
    credit = float(original.get('credit', 0) or 0)
    balance = float(original.get('balance', 0) or 0)
    amount = float(original.get('amount', 0) or 0) or (debit if debit > 0 else credit)
    direction = normalize_direction(debit, credit, original.get('transaction_type', ''))
    
    # Normalize fields
    channel = normalize_channel(normalized.get('channel', ''), original.get('description', ''))
    merchant = normalize_merchant(normalized.get('merchant', ''), original.get('description', ''))
    category = normalize_category(normalized.get('category', ''), merchant, original.get('description', ''))
    reference = str(original.get('reference_number', '') or '').strip()
    description = str(original.get('description', '') or '').strip()
    
    doc = {
        'statementId': statement_id,
        'bankType': bank_code,
        'date': date,
        'amount': amount,
        'direction': direction,
        'balance': balance,
        'channel': channel,
        'merchant': merchant,
        'category': category,
        'reference': reference,
        'description': description,
        'createdAt': datetime.now()
    }
    
    return doc

