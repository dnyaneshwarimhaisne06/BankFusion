"""
Rule-based transaction normalizer (No OpenAI required)
Uses pattern matching to categorize transactions
"""

import re

def normalize_transaction(txn):
    """Normalize transaction using rule-based logic (no API calls)"""
    
    narration = txn.get('narration', '').upper()
    description = txn.get('description', '').upper()
    text = narration or description
    
    # Determine debit or credit
    debit_or_credit = "debit"
    if txn.get('deposit', 0) > 0 or txn.get('credit', 0) > 0:
        debit_or_credit = "credit"
    elif txn.get('withdrawal', 0) > 0 or txn.get('debit', 0) > 0:
        debit_or_credit = "debit"
    
    # Get debit amount for ATM detection
    debit_amount = float(txn.get('debit', 0) or txn.get('withdrawal', 0) or 0)
    
    # Extract merchant
    merchant = extract_merchant(text)
    
    # Categorize (this determines if it's ATM/CASH)
    category = categorize_transaction(text, merchant, debit_amount)
    
    # Handle ATM/CASH transactions - override channel, merchant, transaction_type
    if category == 'cash':
        channel = 'ATM'
        merchant = 'ATM Withdrawal'
        transaction_type = 'withdrawal'
    else:
        # Detect channel for non-ATM transactions
        channel = detect_channel(text)
        # Detect transaction type for non-ATM transactions
        transaction_type = detect_transaction_type(text, debit_or_credit)
    
    return {
        "transaction_type": transaction_type,
        "merchant": merchant,
        "channel": channel,
        "debit_or_credit": debit_or_credit,
        "category": category
    }

def detect_channel(text):
    """Detect payment channel from transaction text"""
    if 'UPI' in text:
        return 'UPI'
    elif 'ATM' in text or 'ATW' in text:
        return 'ATM'
    elif 'NEFT' in text:
        return 'NEFT'
    elif 'RTGS' in text:
        return 'RTGS'
    elif 'IMPS' in text:
        return 'IMPS'
    elif 'POS' in text or 'CARD' in text:
        return 'CARD'
    elif 'ACH' in text:
        return 'ACH'
    elif 'CASH' in text:
        return 'CASH'
    elif 'CHEQUE' in text or 'CHQ' in text:
        return 'CHEQUE'
    elif 'ONLINE' in text or 'IB' in text or 'BILLPAY' in text:
        return 'ONLINE'
    else:
        return 'OTHER'

def detect_transaction_type(text, debit_or_credit):
    """Detect type of transaction"""
    if debit_or_credit == 'credit':
        if 'SALARY' in text or 'SAL' in text:
            return 'salary'
        elif 'TRANSFER' in text or 'IMPS' in text or 'NEFT' in text:
            return 'transfer_received'
        elif 'REFUND' in text or 'REVERSAL' in text:
            return 'refund'
        elif 'INTEREST' in text:
            return 'interest'
        elif 'CASH DEP' in text:
            return 'deposit'
        else:
            return 'credit'
    else:
        if 'ATM' in text or 'ATW' in text:
            return 'withdrawal'
        elif 'POS' in text or 'SWIPE' in text:
            return 'purchase'
        elif 'UPI' in text:
            return 'upi_payment'
        elif 'BILLPAY' in text or 'BILL' in text:
            return 'bill_payment'
        elif 'EMI' in text:
            return 'emi'
        elif 'TRANSFER' in text or 'IMPS' in text or 'NEFT' in text:
            return 'transfer'
        elif 'FEE' in text or 'CHARGE' in text:
            return 'fee'
        else:
            return 'debit'

def extract_merchant(text):
    """Extract merchant name from transaction text - cleans numbers, POS/UPI/ACH codes, IDs"""
    
    # Known brands (for filtering out personal names in UPI)
    known_brands = {
        'AMAZON', 'FLIPKART', 'SWIGGY', 'ZOMATO', 'UBER', 'OLA', 'NETFLIX', 
        'PRIME', 'PAYTM', 'PHONEPE', 'GPAY', 'DMART', 'BIG BAZAAR', 'MORE',
        'RELIANCE', 'HALDIRAM', 'DOMINOS', 'KFC', 'MCDONALD', 'PIZZA HUT',
        'PANTALOONS', 'SHOPPER', 'WESTSIDE', 'LIFESTYLE', 'IRCTC', 'MAKEMYTRIP',
        'GOIBIBO', 'BARBEQUE NATION', 'APOLLO', 'VODAFONE', 'AIRTEL', 'JIO',
        'MYNTRA', 'MEDPLUS', 'MED PLUS', 'SBI CARDS', 'ICICI', 'HDFC', 'AXIS'
    }
    
    # Known merchants mapping
    merchants = {
        'AMAZON': 'Amazon',
        'FLIPKART': 'Flipkart',
        'SWIGGY': 'Swiggy',
        'ZOMATO': 'Zomato',
        'UBER': 'Uber',
        'OLA': 'Ola',
        'NETFLIX': 'Netflix',
        'PRIME': 'Amazon Prime',
        'PAYTM': 'Paytm',
        'PHONEPE': 'PhonePe',
        'GPAY': 'Google Pay',
        'DMART': 'DMart',
        'BIG BAZAAR': 'Big Bazaar',
        'MORE': 'More Supermarket',
        'RELIANCE': 'Reliance',
        'HALDIRAM': 'Haldiram',
        'DOMINOS': 'Dominos Pizza',
        'KFC': 'KFC',
        'MCDONALD': 'McDonalds',
        'PIZZA HUT': 'Pizza Hut',
        'PANTALOONS': 'Pantaloons',
        'SHOPPER': 'Shoppers Stop',
        'WESTSIDE': 'Westside',
        'LIFESTYLE': 'Lifestyle',
        'IRCTC': 'IRCTC',
        'MAKEMYTRIP': 'MakeMyTrip',
        'GOIBIBO': 'Goibibo',
        'BARBEQUE NATION': 'Barbeque Nation',
        'CAFE': 'Cafe',
        'RESTAURANT': 'Restaurant',
        'PETROL': 'Petrol Pump',
        'HOSPITAL': 'Hospital',
        'PHARMACY': 'Pharmacy',
        'APOLLO': 'Apollo',
        'VODAFONE': 'Vodafone',
        'AIRTEL': 'Airtel',
        'JIO': 'Jio',
        'TATA': 'Tata',
        'MYNTRA': 'Myntra',
        'MEDPLUS': 'MedPlus',
        'MED PLUS': 'MedPlus',
        "NATURE'S BASKET": "Nature's Basket",
        "NATURE S BASKET": "Nature's Basket",
        'SPENCERS': "Spencer's",
        "SPENCER'S": "Spencer's",
        'SPENCERS RETAIL': "Spencer's",
        'RELIANCE SMART': 'Reliance Smart',
        'BIGBASKET': 'BigBasket',
        'BIG BASKET': 'BigBasket',
        'BURGER KING': 'Burger King',
        'BURGERKING': 'Burger King',
        'INSTAMART': 'Instamart',
        'MONCHUNIES': 'Monchunies',
        'PVR': 'PVR',
        'INOX': 'INOX',
        'BOOKMYSHOW': 'BookMyShow',
        'RAPIDO': 'Rapido',
        'PRACTO': 'Practo',
        "GOLD'S GYM": "Gold's Gym",
        'GOLDS GYM': "Gold's Gym",
        'CULT FIT': 'Cult.fit',
        'CULTFIT': 'Cult.fit',
        'TALWALKARS': 'Talwalkars',
        'ANYTIME FITNESS': 'Anytime Fitness',
        'INDIAN OIL': 'Indian Oil',
        'IOCL': 'Indian Oil',
        'HPCL': 'HPCL',
        'BHARAT PETROLEUM': 'Bharat Petroleum',
        'VI': 'Vi',
        'BSNL': 'BSNL'
    }
    
    # Check for known merchants first
    for key, value in merchants.items():
        if key in text:
            return value
    
    # Try to extract merchant from UPI transactions
    if 'UPI' in text:
        # Pattern: UPI-XXXX-<merchant>-<reference> or <merchant>@upi
        # Try @upi pattern first
        upi_match = re.search(r'([A-Z][A-Z0-9\s&]+)@[A-Z]+', text)
        if upi_match:
            merchant_name = upi_match.group(1).strip()
            # Check if it's a known brand
            if any(brand in merchant_name.upper() for brand in known_brands):
                return merchant_name.title()
            return merchant_name.title()
        
        # Try dash-separated pattern
        parts = text.split('-')
        for part in parts:
            part_clean = part.strip()
            # Skip if it's just UPI, numbers, or codes
            if part_clean in ['UPI', 'PAYMENT', 'TRANSFER'] or re.match(r'^[A-Z0-9]{4,}$', part_clean):
                continue
            # If it contains known brand, return it
            if any(brand in part_clean.upper() for brand in known_brands):
                return part_clean.title()
            # If it looks like a merchant name (has spaces or is short and alphabetic)
            if len(part_clean) > 2 and (re.search(r'[A-Z][A-Z\s]+[A-Z]', part_clean) or (len(part_clean) < 30 and part_clean.isalpha())):
                return part_clean.title()
    
    # Try to extract from POS transactions
    if 'POS' in text:
        # Remove card numbers and codes, extract merchant name
        # Pattern: POS XXXX-XXXX-XXXX-XXXX MERCHANT NAME
        pos_patterns = [
            r'POS\s+\d+X+\d+\s+([A-Z][A-Z\s&]+?)(?:\s+POS|\s+[0-9]|$)',
            r'POS\s+[0-9X]+\s+([A-Z][A-Z\s&]+?)(?:\s+[0-9]|$)',
            r'[0-9X]{4,}\s+([A-Z][A-Z\s&]{3,})'
        ]
        for pattern in pos_patterns:
            match = re.search(pattern, text)
            if match:
                merchant_name = match.group(1).strip()
                # Clean up common suffixes
                merchant_name = re.sub(r'\s+(POS|CARD|PAYMENT|TRANSACTION)$', '', merchant_name, flags=re.IGNORECASE)
                if merchant_name and len(merchant_name) > 2:
                    return merchant_name.title()
    
    # Generic extraction: remove codes, numbers, IDs, extract merchant name
    # Remove common patterns: UPI codes, transaction IDs, card numbers
    cleaned = re.sub(r'UPI[-\s]*[A-Z0-9]+', '', text)
    cleaned = re.sub(r'[0-9]{10,}', '', cleaned)  # Remove long numbers (transaction IDs)
    cleaned = re.sub(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', '', cleaned)  # Remove card numbers
    cleaned = re.sub(r'ACH[-\s]*[A-Z0-9-]+', '', cleaned)
    cleaned = re.sub(r'POS[-\s]*[A-Z0-9]+', '', cleaned)
    cleaned = re.sub(r'[A-Z]{2,}\d{6,}', '', cleaned)  # Remove codes like ABC123456
    
    # Try to find merchant name (words that are mostly alphabetic)
    words = cleaned.split()
    merchant_words = []
    for word in words:
        word_clean = re.sub(r'[^A-Z]', '', word)
        if len(word_clean) >= 3 and word_clean.isalpha():
            merchant_words.append(word_clean)
            if len(merchant_words) >= 3:  # Limit to reasonable length
                break
    
    if merchant_words:
        return ' '.join(merchant_words).title()
    
    return 'Unknown'

def categorize_transaction(text, merchant, debit_amount=0):
    """
    STRICT GLOBAL RULE-BASED TRANSACTION CLASSIFICATION
    Applies keyword rules in strict priority order.
    NO GUESSING. NO OVERRIDES. KEYWORD RULES HAVE ABSOLUTE PRIORITY.
    """
    
    # ============================================================
    # PRIORITY 1: ATM/CASH (ABSOLUTE PRIORITY - OVERRIDES ALL)
    # ============================================================
    if (('ATM' in text or 'ATW' in text) and 
        ('CASH' in text or 'WDL' in text or 'WITHDRAWAL' in text) and
        debit_amount > 0):
        return 'cash'
    
    # ============================================================
    # PRIORITY 2: INTEREST INCOME
    # ============================================================
    if (re.search(r'\bCREDIT\s+INTEREST\b', text) or 
        re.search(r'\bINTEREST\s+CREDIT\b', text) or 
        re.search(r'\bINTEREST\s+INCOME\b', text) or 
        re.search(r'\bINTEREST\s+PAID\b', text) or
        re.search(r'\bINTEREST\s+ON\s+SAVINGS\b', text) or 
        re.search(r'\bSAVINGS\s+INTEREST\b', text)):
        return 'interest_income'
    
    # ============================================================
    # PRIORITY 3: CREDIT CARD PAYMENT
    # ============================================================
    card_keywords = ['SBI CARDS', 'CARD PAYMENT', 'CARD SETTLEMENT', 'CARD BILL',
                    'CREDIT CARD', 'CARD DUES', 'CARD OUTSTANDING', 'CARD STATEMENT',
                    'CARD MINIMUM', 'CARD AMOUNT', 'CARDS PAYMENT', 'CC PAYMENT',
                    'CARD REPAYMENT']
    if any(kw in text for kw in card_keywords):
        return 'credit_card_payment'
    
    # ============================================================
    # PRIORITY 4: EMI/LOAN (ACH D- with finance keywords)
    # ============================================================
    if re.search(r'ACH\s*D\s*-', text) or re.search(r'ACH-D', text):
        emi_keywords = ['FINANCE', 'NBFC', 'LOAN', 'EMI', 'HOMECREDIT', 'HOME CREDIT', 
                       'HOME', 'INDFIN', 'IND FIN', 'INDIAFIN',
                       'BAJAJ FINANCE', 'HDFC BANK', 'ICICI BANK', 'AXIS BANK',
                       'KOTAK', 'FULLERTON', 'CAPITAL FIRST', 'IDFC', 'ADITYA BIRLA']
        if any(kw in text for kw in emi_keywords):
            return 'emi_loan'
    
    # ============================================================
    # PRIORITY 5: FOOD & DINING
    # ============================================================
    food_keywords = ['SWIGGY', 'ZOMATO', 'MCDONALD', 'MCDONALDS', 'KFC', 
                    'BURGER KING', 'BURGERKING', 'INSTAMART', 
                    'BARBEQUE NATION', 'BARBEQUE', 'MONCHUNIES', 
                    'DOMINOS', 'DOMINO', 'PIZZA HUT', 'PIZZA',
                    'HALDIRAM', 'HALDIRAMS']
    if any(kw in text for kw in food_keywords):
        return 'food_dining'
    
    # ============================================================
    # PRIORITY 6: GROCERIES
    # ============================================================
    grocery_keywords = ['SPENCERS', "SPENCER'S", 'SPENCERS RETAIL',
                       'DMART', "D'MART",
                       'BIG BAZAAR', 'BIGBAZAAR',
                       'RELIANCE SMART', 'RELIANCE',
                       "NATURE'S BASKET", 'NATURE S BASKET', 'NATURE BASKET',
                       'BIGBASKET', 'BIG BASKET']
    if any(kw in text for kw in grocery_keywords):
        return 'groceries'
    
    # ============================================================
    # PRIORITY 7: ENTERTAINMENT
    # ============================================================
    entertainment_keywords = ['CINEMA', 'MOVIE', 'PVR', 'INOX', 'BOOKMYSHOW']
    if any(kw in text for kw in entertainment_keywords):
        return 'entertainment'
    
    # ============================================================
    # PRIORITY 8: TRAVEL
    # ============================================================
    travel_keywords = ['OLA', 'UBER', 'RAPIDO',
                      'PMPML', 'PMPL', 'BUS PASS', 'BUS TICKET',
                      'REDBUS', 'RED BUS',
                      'IRCTC', 'METRO',
                      'MAKE MY TRIP', 'MAKEMYTRIP']
    if any(kw in text for kw in travel_keywords):
        return 'travel'
    
    # ============================================================
    # PRIORITY 9: HEALTHCARE
    # ============================================================
    health_keywords = ['PRACTO',
                      'GYM', 'FITNESS', "GOLD'S GYM", "GOLDS GYM", 
                      'CULT FIT', 'CULTFIT',
                      'TALWALKARS', 'ANYTIME FITNESS',
                      'HOSPITAL', 'PHARMACY', 'MEDICAL', 'MEDPLUS', 'MED PLUS']
    if any(kw in text for kw in health_keywords):
        return 'healthcare'
    
    # ============================================================
    # PRIORITY 10: FUEL
    # ============================================================
    fuel_keywords = ['INDIAN OIL', 'IOCL',
                    'HP', 'HPCL',
                    'BPCL', 'BHARAT PETROLEUM',
                    'PETROL PUMP', 'FUEL', 'PETROL', 'DIESEL']
    if any(kw in text for kw in fuel_keywords):
        return 'fuel'
    
    # ============================================================
    # PRIORITY 11: BILLS & UTILITIES
    # ============================================================
    bill_keywords = ['AIRTEL', 'JIO', 'VODAFONE', 'VI', 'BSNL',
                    'FIBER', 'BROADBAND', 'DTH']
    if any(kw in text for kw in bill_keywords):
        return 'bills_utilities'
    
    # ============================================================
    # PRIORITY 12: TRANSFER
    # ============================================================
    transfer_keywords = ['NEFT', 'IMPS', 'RTGS', 'BANK TRANSFER', 'UPI P2P']
    if any(kw in text for kw in transfer_keywords):
        return 'transfer'
    
    # ============================================================
    # FINAL: OTHERS (only if NO rule matches)
    # ============================================================
    return 'others'
