"""
HYBRID Transaction Normalizer
Rule-based and OpenAI are SUGGESTIONS ONLY
apply_global_rules() is the FINAL AUTHORITY
"""

import re
import os
from rule_based_normalizer import normalize_transaction as rule_based_normalize
from typing import Dict

# Optional OpenAI import (graceful fallback if not available)
try:
    from openai_normalizer_enhanced import normalize_transaction_with_openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    def normalize_transaction_with_openai(txn: Dict) -> Dict:
        """Fallback when OpenAI is not available"""
        return {}

def is_openai_enabled() -> bool:
    return OPENAI_AVAILABLE and os.getenv('DISABLE_OPENAI_NORMALIZATION', '0') != '1'

# Known brand mappings (module-level for use in multiple functions)
KNOWN_BRANDS = {
        'SWIGGY': 'Swiggy',
        'ZOMATO': 'Zomato',
        'MCDONALD': 'McDonalds',
        'MCDONALDS': 'McDonalds',
        'KFC': 'KFC',
        'BURGER KING': 'Burger King',
        'BURGERKING': 'Burger King',
        'INSTAMART': 'Instamart',
        'BARBEQUE NATION': 'Barbeque Nation',
        'BARBEQUE': 'Barbeque Nation',
        'MONCHUNIES': 'Monchunies',
        'DOMINOS': 'Dominos Pizza',
        'DOMINO': 'Dominos Pizza',
        'PIZZA HUT': 'Pizza Hut',
        'PIZZA': 'Pizza',
        'SUBWAY': 'Subway',
        'HALDIRAM': 'Haldiram',
        'HALDIRAMS': 'Haldiram',
        'SPENCERS': "Spencer's",
        "SPENCER'S": "Spencer's",
        'SPENCER': "Spencer's",
        'SPENCERS RETAIL': "Spencer's",
        'DMART': 'DMart',
        "D'MART": 'DMart',
        'BIG BAZAAR': 'Big Bazaar',
        'BIGBAZAAR': 'Big Bazaar',
        'RELIANCE SMART': 'Reliance Smart',
        'RELIANCE': 'Reliance',
        "NATURE'S BASKET": "Nature's Basket",
        'NATURE S BASKET': "Nature's Basket",
        'NATURE BASKET': "Nature's Basket",
        'BIGBASKET': 'BigBasket',
        'BIG BASKET': 'BigBasket',
        'GROFERS': 'Grofers',
        'AJIO': 'AJIO',
        'AMAZON': 'Amazon',
        'FLIPKART': 'Flipkart',
        'MYNTRA': 'Myntra',
        'PANTALOONS': 'Pantaloons',
        'WESTSIDE': 'Westside',
        'LIFESTYLE': 'Lifestyle',
        'SHOPPER': 'Shoppers Stop',
        'PVR': 'PVR',
        'PVR CINEMAS': 'PVR Cinemas',
        'CINEPOLIS': 'Cinepolis',
        'INOX': 'INOX',
        'BOOKMYSHOW': 'BookMyShow',
        'CINEMA': 'Cinema',
        'MOVIE': 'Movie',
        'OLA': 'Ola',
        'UBER': 'Uber',
        'RAPIDO': 'Rapido',
        'IRCTC': 'IRCTC',
        'METRO': 'Metro',
        'REDBUS': 'RedBus',
        'RED BUS': 'RedBus',
        'PMPML': 'PMPML',
        'PMPL': 'PMPML',
        'MAKE MY TRIP': 'MakeMyTrip',
        'MAKEMYTRIP': 'MakeMyTrip',
        'GOIBIBO': 'Goibibo',
        'GO IBIBO': 'Goibibo',
        'PRACTO': 'Practo',
        "GOLD'S GYM": "Gold's Gym",
        'GOLDS GYM': "Gold's Gym",
        'GYM': 'Gym',
        'FITNESS': 'Fitness',
        'CULT FIT': 'Cult.fit',
        'CULTFIT': 'Cult.fit',
        'TALWALKARS': 'Talwalkars',
        'ANYTIME FITNESS': 'Anytime Fitness',
        'HOSPITAL': 'Hospital',
        'FORTIS': 'Fortis',
        'APOLLO': 'Apollo',
        'PHARMACY': 'Pharmacy',
        'MEDICAL': 'Medical',
        'MEDPLUS': 'MedPlus',
        'MED PLUS': 'MedPlus',
        'INDIAN OIL': 'Indian Oil',
        'IOCL': 'Indian Oil',
        'HP': 'HP',
        'HPCL': 'HPCL',
        'BPCL': 'Bharat Petroleum',
        'BHARAT PETROLEUM': 'Bharat Petroleum',
        'SHELL': 'Shell',
        'PETROL PUMP': 'Petrol Pump',
        'AIRTEL': 'Airtel',
        'JIO': 'Jio',
        'VODAFONE': 'Vodafone',
        'VI': 'Vi',
        'BSNL': 'BSNL',
        'FIBER': 'Fiber',
        'BROADBAND': 'Broadband',
        'DTH': 'DTH',
        'ELECTRICITY': 'Electricity',
        'GAS': 'Gas',
        'LIC': 'LIC',
        'HDFC LIFE': 'HDFC Life',
        'HDFCLIFE': 'HDFC Life'
}

# Known employers for salary detection
KNOWN_EMPLOYERS = [
    'TCS', 'TATA CONSULTANCY', 'TATA CONSULTANCY SERVICES',
    'INFOSYS', 'INFOSYS TECHNOLOGIES',
    'WIPRO', 'WIPRO TECHNOLOGIES',
    'HCL', 'HCL TECHNOLOGIES',
    'ACCENTURE',
    'COGNIZANT', 'CTS',
    'IBM', 'IBM INDIA',
    'MICROSOFT', 'MICROSOFT INDIA',
    'GOOGLE', 'GOOGLE INDIA',
    'AMAZON', 'AMAZON INDIA',
    'FLIPKART',
    'PAYTM', 'PAYTM PAYMENTS',
    'ZOMATO',
    'SWIGGY',
    'OYO', 'OYO ROOMS',
    'OLA', 'OLA CABS',
    'UBER', 'UBER INDIA',
    'RELIANCE', 'RELIANCE INDUSTRIES',
    'TATA', 'TATA GROUP',
    'MAHINDRA', 'MAHINDRA & MAHINDRA',
    'BAJAJ', 'BAJAJ AUTO',
    'MARUTI', 'MARUTI SUZUKI',
    'HDFC', 'HDFC BANK',
    'ICICI', 'ICICI BANK',
    'AXIS', 'AXIS BANK',
    'SBI', 'STATE BANK OF INDIA',
    'KOTAK', 'KOTAK MAHINDRA BANK',
    'YES BANK',
    'INDUSIND', 'INDUSIND BANK'
]


def extract_merchant_from_text(text: str) -> str:
    """
    Extract merchant name from transaction text.
    CRITICAL: Person-name detection MUST run BEFORE brand detection.
    Pattern: CR/NAME /BANK/upi_id → merchant = NAME
    """
    text_upper = text.upper()
    
    # ============================================================
    # STEP 1: PERSON-NAME DETECTION (MUST RUN BEFORE BRAND DETECTION)
    # ============================================================
    # Pattern: CR/NAME /BANK/upi_id or DR/NAME /BANK/upi_id
    # Extract person name FIRST, before checking brands
    cr_name_match = re.search(r'CR/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
    if cr_name_match:
        person_name = cr_name_match.group(1).strip()
        # Clean up (remove UPI handles, bank codes, etc.)
        person_name = re.sub(r'@.*$', '', person_name).strip()
        person_name = re.sub(r'\s+/.*$', '', person_name).strip()
        if person_name and len(person_name) > 1:
            # Quick check: if it's clearly a person name (not a brand keyword), return it
            # Person names are typically short (2-20 chars), no common brand keywords
            is_likely_person = True
            common_brand_keywords = ['SWIGGY', 'ZOMATO', 'AMAZON', 'FLIPKART', 'DMART', 'RELIANCE', 
                                   'AIRTEL', 'JIO', 'LIC', 'HDFC', 'PVR', 'BOOKMYSHOW', 'DOMINOS']
            person_upper = person_name.upper()
            for brand_kw in common_brand_keywords:
                if brand_kw in person_upper:
                    is_likely_person = False
                    break
            
            if is_likely_person:
                return person_name.title()
    
    dr_name_match = re.search(r'DR/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
    if dr_name_match:
        person_name = dr_name_match.group(1).strip()
        person_name = re.sub(r'@.*$', '', person_name).strip()
        person_name = re.sub(r'\s+/.*$', '', person_name).strip()
        if person_name and len(person_name) > 1:
            is_likely_person = True
            person_upper = person_name.upper()
            common_brand_keywords = ['SWIGGY', 'ZOMATO', 'AMAZON', 'FLIPKART', 'DMART', 'RELIANCE',
                                   'AIRTEL', 'JIO', 'LIC', 'HDFC', 'PVR', 'BOOKMYSHOW', 'DOMINOS']
            for brand_kw in common_brand_keywords:
                if brand_kw in person_upper:
                    is_likely_person = False
                    break
            
            if is_likely_person:
                return person_name.title()
    
    # ============================================================
    # STEP 2: UPI PATTERNS (UPIAB, UPIAR, MOBFT)
    # ============================================================
    if any(keyword in text_upper for keyword in ['UPIAB', 'UPIAR', 'MOBFT', 'UPI']):
        # Pattern: UPIAR/<txn-id>/(DR|CR)/<MERCHANT> /<BANK>/<upi-handle>
        upiar_match = re.search(r'UPIAR/[^/]+/(DR|CR)/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
        if upiar_match:
            merchant_segment = upiar_match.group(2).strip()
            merchant_segment = re.sub(r'\s+/.*$', '', merchant_segment).strip()
            if merchant_segment and len(merchant_segment) > 1:
                # Check if it's a known brand
                sorted_brands = sorted(KNOWN_BRANDS.items(), key=lambda x: len(x[0]), reverse=True)
                for brand_key, brand_name in sorted_brands:
                    if brand_key in merchant_segment.upper():
                        return brand_name
                # Return merchant name as-is
                return merchant_segment.title()
        
        # Pattern: UPIAB/<txn-id>/(DR|CR)/<MERCHANT> /<BANK>/<upi-handle>
        upiab_match = re.search(r'UPIAB/[^/]+/(DR|CR)/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
        if upiab_match:
            merchant_segment = upiab_match.group(2).strip()
            merchant_segment = re.sub(r'\s+/.*$', '', merchant_segment).strip()
            if merchant_segment and len(merchant_segment) > 1:
                sorted_brands = sorted(KNOWN_BRANDS.items(), key=lambda x: len(x[0]), reverse=True)
                for brand_key, brand_name in sorted_brands:
                    if brand_key in merchant_segment.upper():
                        return brand_name
                return merchant_segment.title()
    
    # ============================================================
    # STEP 3: BRAND DETECTION (AFTER person-name check)
    # ============================================================
    sorted_brands = sorted(KNOWN_BRANDS.items(), key=lambda x: len(x[0]), reverse=True)
    for brand_key, brand_name in sorted_brands:
        pattern = r'\b' + re.escape(brand_key) + r'\b'
        if re.search(pattern, text_upper):
            return brand_name
    
    # Try to extract from POS patterns
    if 'POS' in text_upper:
        pos_match = re.search(r'POS\s+\d+X+\d+\s+([A-Z][A-Z\s&]+?)(?:\s+POS|\s+[0-9]|$)', text_upper)
        if pos_match:
            merchant_name = pos_match.group(1).strip()
            if merchant_name and len(merchant_name) > 2:
                return merchant_name.title()
    
    return 'Unknown'


def apply_global_rules(text: str, suggested_result: Dict, debit_amount: float, credit_amount: float = 0) -> Dict:
    """
    FINAL AUTHORITY - This function is the compliance officer.
    Rules ALWAYS override suggestions from rule-based or OpenAI.
    NO EXCEPTIONS.
    Uses WORD-BOUNDARY regex to prevent substring matching bugs.
    
    CRITICAL: Channel keywords (UPI, IMPS, NEFT, RTGS) NEVER decide category.
    They only set channel & transaction_type.
    
    NO EARLY RETURNS - All rules are checked, highest priority wins.
    """
    text_upper = text.upper()
    
    # Initialize final result with suggestion
    final_result = {
        'transaction_type': suggested_result.get('transaction_type', 'debit'),
        'merchant': suggested_result.get('merchant', 'Unknown'),
        'channel': suggested_result.get('channel', 'OTHER'),
        'debit_or_credit': suggested_result.get('debit_or_credit', 'debit'),
        'category': suggested_result.get('category', 'transfer').lower()  # Default to transfer, never "others"
    }
    
    # Extract merchant FIRST (before category logic)
    extracted_merchant = extract_merchant_from_text(text_upper)
    if extracted_merchant != 'Unknown':
        final_result['merchant'] = extracted_merchant
    
    # ============================================================
    # STEP 1: CHANNEL DETECTION (PATTERN-BASED ONLY)
    # ============================================================
    # Channel detection is pattern-based ONLY - merchant must NOT decide channel
    # Pattern mappings:
    # CWDR → CASH
    # BUPI → UPI
    # MEDR → CARD
    # NEFT → NEFT
    # NACH → ACH
    # UPI → UPI
    # IMPS → IMPS
    # RTGS → RTGS
    # ATM → ATM
    
    if re.search(r'\bCWDR\b', text_upper):
        final_result['channel'] = 'CASH'
    elif re.search(r'\bBUPI\b', text_upper):
        final_result['channel'] = 'UPI'
    elif re.search(r'\bMEDR\b', text_upper):
        final_result['channel'] = 'CARD'
    elif re.search(r'\bNACH\b', text_upper):
        final_result['channel'] = 'ACH'
    elif re.search(r'\bUPIAB\b', text_upper) or re.search(r'\bUPIAR\b', text_upper):
        final_result['channel'] = 'UPI'
    elif re.search(r'\bMOBFT\b', text_upper):
        final_result['channel'] = 'UPI'  # MOBFT is mobile banking, treat as UPI
    elif re.search(r'\bUPI\b', text_upper):
        final_result['channel'] = 'UPI'
    elif re.search(r'\bIMPS\b', text_upper):
        final_result['channel'] = 'IMPS'
    elif re.search(r'\bNEFT\b', text_upper):
        final_result['channel'] = 'NEFT'
    elif re.search(r'\bRTGS\b', text_upper):
        final_result['channel'] = 'RTGS'
    elif re.search(r'\bATM\b', text_upper) or re.search(r'ATW-', text_upper):
        final_result['channel'] = 'ATM'
    
    # ============================================================
    # STEP 2: CATEGORY RULES (STRICT PRIORITY ORDER - INTENT FIRST)
    # ============================================================
    # ALL category decisions happen here, overriding rule-based and OpenAI suggestions
    # NO EARLY RETURNS - Check all rules, apply highest priority match
    # 
    # MANDATORY PRIORITY ORDER (STRICT - INTENT FIRST - DO NOT CHANGE):
    # 🧠 INTENT-FIRST APPROACH: DO NOT use channel or debit/credit to decide category
    # Determine intent ONLY from description text using this priority:
    # 
    # 1️⃣ EMI / LOAN (HIGHEST PRIORITY)
    #    → transaction_type: "loan_payment", category: "emi_loan"
    #    ❌ NEVER classify EMI as transfer
    # 
    # 2️⃣ EDUCATION FEES
    #    → transaction_type: "expense", category: "education"
    #    ❌ NEVER classify education as transfer
    # 
    # 3️⃣ TRAVEL BOOKINGS
    #    → transaction_type: "expense", category: "travel"
    #    ❌ NEVER classify travel platforms as transfer
    # 
    # 4️⃣ P2P TRANSFER (VERY STRICT)
    #    → transaction_type: "transfer", category: "transfer"
    #    ONLY IF: UPI contains PERSON NAME OR @upi without known merchant OR NEFT/IMPS with individual name
    #    ❌ Brands ≠ transfer, Services ≠ transfer
    # 
    # 5. ATM / CASH WDL → cash
    # 6. BILLS & UTILITIES → bills_utilities
    # 7. FUEL → fuel
    # 8. GROCERIES → groceries
    # 9. FOOD & DINING → food_dining
    # 10. ENTERTAINMENT → entertainment
    # 11. SHOPPING → shopping
    # 12. HEALTHCARE → healthcare
    # 13. RENT → rent
    # 14. INSURANCE → insurance
    # 15. INCOME (SALARY) → income
    # 16. TRANSFER (LAST option - only if NONE OF ABOVE match)
    # ❌ NEVER USE "others" - if any keyword/brand/intent exists, classify it
    
    matched_priority = 999  # Higher number = lower priority
    matched_category = None
    matched_merchant = None
    matched_transaction_type = None
    matched_channel = None
    matched_debit_or_credit = None
    
    # ============================================================
    # PRIORITY 1: EMI / LOAN (HIGHEST PRIORITY - INTENT FIRST)
    # ============================================================
    # EMI/LOAN OVERRIDE: If description contains EMI/LOAN keywords
    # THEN: transaction_type = "loan_payment", category = "emi_loan"
    # MUST NOT be transfer, MUST NOT be others
    # Channel remains UPI / NEFT / ACH (payment method, not purpose)
    # Purpose decides category, not payment method
    has_emi_loan_keyword = False
    loan_type = None
    
    # Check for specific loan types (order matters - check more specific first)
    if re.search(r'\bHOME\s+LOAN\s+EMI\b', text_upper) or re.search(r'\bHOUSING\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'HOME_LOAN'
    elif re.search(r'\bHOME\s+LOAN\b', text_upper) or re.search(r'\bHOUSING\s+LOAN\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'HOME_LOAN'
    elif re.search(r'\bPERSONAL\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'PERSONAL_LOAN'
    elif re.search(r'\bPERSONAL\s+LOAN\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'PERSONAL_LOAN'
    elif re.search(r'\bCAR\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'CAR_LOAN'
    elif re.search(r'\bCAR\s+LOAN\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'CAR_LOAN'
    elif re.search(r'\bEDUCATION\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'EDUCATION_LOAN'
    elif re.search(r'\bEDUCATION\s+LOAN\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'EDUCATION_LOAN'
    elif re.search(r'\bCREDIT\s+CARD\s+EMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'CREDIT_CARD_EMI'
    elif re.search(r'\bLOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'LOAN_EMI'
    elif re.search(r'\bHOMECRINDFIN\b', text_upper) or re.search(r'\bHOME\s+CREDIT\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'HOME_CREDIT'
    elif re.search(r'\bACH\s+D-\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'ACH_LOAN'
    elif re.search(r'\bNBFC\b', text_upper) or re.search(r'\bFINANCE\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'LOAN'
    elif re.search(r'\bEMI\b', text_upper):
        has_emi_loan_keyword = True
        loan_type = 'EMI'
    
    if has_emi_loan_keyword:
        if 1 < matched_priority:
            matched_priority = 1
            matched_category = 'emi_loan'
            matched_transaction_type = 'loan_payment'
            # Set merchant based on detected loan type
            if loan_type == 'HOME_LOAN':
                matched_merchant = 'Home Loan EMI'
            elif loan_type == 'PERSONAL_LOAN':
                matched_merchant = 'Personal Loan EMI'
            elif loan_type == 'CAR_LOAN':
                matched_merchant = 'Car Loan EMI'
            elif loan_type == 'EDUCATION_LOAN':
                matched_merchant = 'Education Loan EMI'
            elif loan_type == 'CREDIT_CARD_EMI':
                matched_merchant = 'Credit Card EMI'
            elif loan_type == 'HOME_CREDIT':
                matched_merchant = 'Home Credit EMI'
            elif loan_type == 'LOAN_EMI':
                matched_merchant = 'Loan EMI Payment'
            elif loan_type == 'EMI':
                matched_merchant = 'EMI Payment'
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else 'Loan EMI Payment'
    
    # ============================================================
    # PRIORITY 2: EDUCATION FEES (INTENT FIRST)
    # ============================================================
    # EDUCATION OVERRIDE: If description contains education keywords
    # THEN: transaction_type = "expense", category = "education"
    # MUST NOT be transfer, MUST NOT be others
    # Channel remains UPI (or whatever was detected)
    # Purpose decides category, not payment method
    if (re.search(r'\bSCHOOL\b', text_upper) or
        re.search(r'\bSCHOOL\s+FEES\b', text_upper) or
        re.search(r'\bSCHOOLFEES\b', text_upper) or
        re.search(r'\bEDUCATION\b', text_upper) or
        re.search(r'\bCOLLEGE\b', text_upper) or
        re.search(r'\bUNIVERSITY\b', text_upper) or
        re.search(r'\bTUITION\b', text_upper) or
        re.search(r'\bADMISSION\b', text_upper) or
        re.search(r'\bFEES\b', text_upper)):
        if 2 < matched_priority:
            matched_priority = 2
            matched_category = 'education'
            matched_transaction_type = 'expense'
            # Set merchant based on detected education keyword
            if re.search(r'\bSCHOOL\s+FEES\b', text_upper) or re.search(r'\bSCHOOLFEES\b', text_upper):
                matched_merchant = 'School Fees'
            elif re.search(r'\bSCHOOL\b', text_upper):
                matched_merchant = 'School'
            elif re.search(r'\bCOLLEGE\b', text_upper):
                matched_merchant = 'College'
            elif re.search(r'\bUNIVERSITY\b', text_upper):
                matched_merchant = 'University'
            elif re.search(r'\bTUITION\b', text_upper):
                matched_merchant = 'Tuition'
            elif re.search(r'\bADMISSION\b', text_upper):
                matched_merchant = 'Admission'
            elif re.search(r'\bFEES\b', text_upper):
                matched_merchant = 'Fees'
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else 'Education'
    
    # ============================================================
    # PRIORITY 3: TRAVEL BOOKINGS (INTENT FIRST)
    # ============================================================
    # TRAVEL BOOKINGS OVERRIDE: If description contains travel booking platforms
    # THEN: transaction_type = "expense", category = "travel"
    # MUST NOT be transfer, MUST NOT be others
    # Travel platforms: IRCTC, YATRA, CLEARTRIP, MAKE MY TRIP, FLIGHT, HOTEL
    if (re.search(r'\bIRCTC\b', text_upper) or
        re.search(r'\bYATRA\b', text_upper) or
        re.search(r'\bCLEARTRIP\b', text_upper) or
        re.search(r'\bMAKE\s+MY\s+TRIP\b', text_upper) or
        re.search(r'\bMAKEMYTRIP\b', text_upper) or
        re.search(r'\bFLIGHT\b', text_upper) or
        re.search(r'\bHOTEL\b', text_upper)):
        if 3 < matched_priority:
            matched_priority = 3
            matched_category = 'travel'
            matched_transaction_type = 'expense'
            # Set merchant based on detected travel platform
            if re.search(r'\bIRCTC\b', text_upper):
                matched_merchant = 'IRCTC'
            elif re.search(r'\bYATRA\b', text_upper):
                matched_merchant = 'Yatra'
            elif re.search(r'\bCLEARTRIP\b', text_upper):
                matched_merchant = 'Cleartrip'
            elif re.search(r'\bMAKE\s+MY\s+TRIP\b', text_upper) or re.search(r'\bMAKEMYTRIP\b', text_upper):
                matched_merchant = 'MakeMyTrip'
            elif re.search(r'\bFLIGHT\b', text_upper):
                matched_merchant = 'Flight Booking'
            elif re.search(r'\bHOTEL\b', text_upper):
                matched_merchant = 'Hotel Booking'
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else 'Travel Booking'
    
    # ============================================================
    # PRIORITY 4: ATM / CASH (ABSOLUTE OVERRIDE)
    # ============================================================
    # Do NOT match if it's a cash deposit (CASH DEP, CASH DEPOSIT, or MICRO ATM CASH DEP)
    is_cash_deposit = (re.search(r'\bCASH\s+DEP\b', text_upper) or 
                      re.search(r'\bCASH\s+DEPOSIT\b', text_upper) or
                      re.search(r'\bMICRO\s+ATM\s+CASH\s+DEP\b', text_upper))
    
    if (re.search(r'ATW-', text_upper) or re.search(r'\bATM\b', text_upper)) and not is_cash_deposit:
        if 4 < matched_priority:
            matched_priority = 4
            matched_category = 'cash'
            matched_merchant = 'ATM Withdrawal'
            matched_transaction_type = 'withdrawal'
            matched_channel = 'ATM'
            matched_debit_or_credit = 'debit'
    
    # Cash deposit
    if (re.search(r'\bCASH\s+DEP\b', text_upper) or 
        re.search(r'\bCASH\s+DEPOSIT\b', text_upper) or
        re.search(r'\bMICRO\s+ATM\s+CASH\s+DEP\b', text_upper)):
        if 4 < matched_priority:
            matched_priority = 4
            matched_category = 'cash'
            matched_merchant = 'Cash Deposit'
            matched_transaction_type = 'credit'
            matched_channel = 'CASH'
            matched_debit_or_credit = 'credit'
    
    # ============================================================
    # PRIORITY 5: FUEL (ONLY FOR PETROL PUMPS - NOT GAS PAYMENTS)
    # ============================================================
    # Fuel is ONLY for petrol pumps, NOT for gas utility payments
    # Only classify as "fuel" if description contains:
    # PETROL PUMP, IOCL, BPCL, HPCL, INDIAN OIL, BHARAT PETROLEUM
    # The word "GAS" alone ≠ fuel. "GAS PAYMENT" or "GAS BILL" = bills_utilities
    # 
    # Check if this is a utility payment first (if so, skip fuel)
    is_utility_payment = (re.search(r'\bGAS\s+PAYMENT\b', text_upper) or
                          re.search(r'\bGAS\s+BILL\b', text_upper) or
                          re.search(r'\bLPG\b', text_upper) or
                          re.search(r'\bELECTRICITY\b', text_upper) or
                          re.search(r'\bPOWER\b', text_upper) or
                          re.search(r'\bDISCOM\b', text_upper) or
                          re.search(r'\bMSEDCL\b', text_upper) or
                          re.search(r'\bMSEB\b', text_upper) or
                          re.search(r'\bBESCOM\b', text_upper) or
                          re.search(r'\bTANGEDCO\b', text_upper))
    
    if not is_utility_payment:
        if (re.search(r'\bPETROL\s+PUMP\b', text_upper) or
            re.search(r'\bIOCL\b', text_upper) or
            re.search(r'\bBPCL\b', text_upper) or
            re.search(r'\bHPCL\b', text_upper) or
            re.search(r'\bINDIAN\s+OIL\b', text_upper) or
            re.search(r'\bBHARAT\s+PETROLEUM\b', text_upper) or
            re.search(r'\bHP\b', text_upper) or
            re.search(r'\bSHELL\b', text_upper) or
            (re.search(r'\bPETROL\b', text_upper) and not re.search(r'\bGAS\b', text_upper)) or
            (re.search(r'\bFUEL\b', text_upper) and not re.search(r'\bGAS\b', text_upper)) or
            re.search(r'\bDIESEL\b', text_upper)):
            if 5 < matched_priority:
                matched_priority = 5
                matched_category = 'fuel'
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 6: BILLS & UTILITIES (ABSOLUTE - OVERRIDES TRANSFER AND FUEL)
    # ============================================================
    # UTILITIES MUST OVERRIDE EVERYTHING (ABSOLUTE RULE)
    # If description contains ANY utility keyword:
    # ELECTRICITY, POWER, DISCOM, MSEDCL, MSEB, BESCOM, TANGEDCO
    # GAS PAYMENT, GAS BILL, LPG
    # AIRTEL, JIO, VI, BSNL (with service words)
    # BROADBAND, FIBER, DTH
    # THEN: category = "bills_utilities"
    # MUST NOT be "transfer"
    # MUST NOT be "fuel"
    
    # Check for utility keywords (electricity, gas, power companies)
    has_utility_keyword = (re.search(r'\bELECTRICITY\b', text_upper) or
                           re.search(r'\bPOWER\b', text_upper) or
                           re.search(r'\bDISCOM\b', text_upper) or
                           re.search(r'\bMSEDCL\b', text_upper) or
                           re.search(r'\bMSEB\b', text_upper) or
                           re.search(r'\bBESCOM\b', text_upper) or
                           re.search(r'\bTANGEDCO\b', text_upper) or
                           re.search(r'\bGAS\s+PAYMENT\b', text_upper) or
                           re.search(r'\bGAS\s+BILL\b', text_upper) or
                           re.search(r'\bLPG\b', text_upper) or
                           re.search(r'\bFIBER\b', text_upper) or
                           re.search(r'\bBROADBAND\b', text_upper) or
                           re.search(r'\bDTH\b', text_upper) or
                           re.search(r'\bINTERNET\s+PAYMENT\b', text_upper) or
                           re.search(r'\bINTERNET\b', text_upper))
    
    # Check for telecom brands with service words
    has_telecom_service = False
    telecom_brand = None
    if re.search(r'\bJIO\b', text_upper):
        if (re.search(r'\bRECHARGE\b', text_upper) or
            re.search(r'\bBILL\b', text_upper) or
            re.search(r'\bFIBER\b', text_upper) or
            re.search(r'\bBROADBAND\b', text_upper) or
            re.search(r'\bDTH\b', text_upper)):
            has_telecom_service = True
            telecom_brand = 'Jio'
            has_utility_keyword = True
    elif re.search(r'\bAIRTEL\b', text_upper):
        if (re.search(r'\bRECHARGE\b', text_upper) or
            re.search(r'\bBILL\b', text_upper) or
            re.search(r'\bFIBER\b', text_upper) or
            re.search(r'\bBROADBAND\b', text_upper) or
            re.search(r'\bDTH\b', text_upper)):
            has_telecom_service = True
            telecom_brand = 'Airtel'
            has_utility_keyword = True
    elif re.search(r'\bVI\b', text_upper):
        if (re.search(r'\bRECHARGE\b', text_upper) or
            re.search(r'\bBILL\b', text_upper) or
            re.search(r'\bFIBER\b', text_upper) or
            re.search(r'\bBROADBAND\b', text_upper) or
            re.search(r'\bDTH\b', text_upper)):
            has_telecom_service = True
            telecom_brand = 'Vi'
            has_utility_keyword = True
    elif re.search(r'\bVODAFONE\b', text_upper):
        if (re.search(r'\bRECHARGE\b', text_upper) or
            re.search(r'\bBILL\b', text_upper) or
            re.search(r'\bFIBER\b', text_upper) or
            re.search(r'\bBROADBAND\b', text_upper) or
            re.search(r'\bDTH\b', text_upper)):
            has_telecom_service = True
            telecom_brand = 'Vodafone'
            has_utility_keyword = True
    elif re.search(r'\bBSNL\b', text_upper):
        if (re.search(r'\bRECHARGE\b', text_upper) or
            re.search(r'\bBILL\b', text_upper) or
            re.search(r'\bFIBER\b', text_upper) or
            re.search(r'\bBROADBAND\b', text_upper) or
            re.search(r'\bDTH\b', text_upper)):
            has_telecom_service = True
            telecom_brand = 'BSNL'
            has_utility_keyword = True
    
    if has_utility_keyword:
        if 6 < matched_priority:
            matched_priority = 6
            matched_category = 'bills_utilities'
            # Set merchant based on detected utility
            if telecom_brand:
                matched_merchant = telecom_brand
            elif re.search(r'\bMSEDCL\b', text_upper):
                matched_merchant = 'MSEDCL'
            elif re.search(r'\bMSEB\b', text_upper):
                matched_merchant = 'MSEB'
            elif re.search(r'\bBESCOM\b', text_upper):
                matched_merchant = 'BESCOM'
            elif re.search(r'\bTANGEDCO\b', text_upper):
                matched_merchant = 'TANGEDCO'
            elif re.search(r'\bDISCOM\b', text_upper):
                matched_merchant = 'DISCOM'
            elif re.search(r'\bELECTRICITY\b', text_upper) or re.search(r'\bPOWER\b', text_upper):
                matched_merchant = 'Electricity'
            elif re.search(r'\bGAS\s+PAYMENT\b', text_upper) or re.search(r'\bGAS\s+BILL\b', text_upper) or re.search(r'\bLPG\b', text_upper):
                matched_merchant = 'Gas'
            elif re.search(r'\bGAS\b', text_upper):
                # Only if it's not a petrol pump context
                if not (re.search(r'\bPETROL\b', text_upper) or re.search(r'\bFUEL\b', text_upper)):
                    matched_merchant = 'Gas'
                else:
                    matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
            elif re.search(r'\bINTERNET\b', text_upper):
                matched_merchant = 'Internet Service'
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 7: GROCERIES
    # ============================================================
    # Check if telecom keywords are present (if so, skip groceries - JIO OVERRIDES RELIANCE)
    # BUT: Fuel keywords already checked above, so RELIANCE PETROL → fuel (not groceries)
    has_telecom = (re.search(r'\bJIO\b', text_upper) or
                   re.search(r'\bAIRTEL\b', text_upper) or
                   re.search(r'\bVODAFONE\b', text_upper) or
                   re.search(r'\bVI\b', text_upper) or
                   re.search(r'\bBSNL\b', text_upper))
    
    # Also check if fuel keywords exist (if so, skip groceries)
    has_fuel = (re.search(r'\bPETROL\b', text_upper) or
                re.search(r'\bFUEL\b', text_upper) or
                re.search(r'\bBPCL\b', text_upper) or
                re.search(r'\bHPCL\b', text_upper) or
                re.search(r'\bIOCL\b', text_upper))
    
    # Check if telecom keywords are present (if so, skip groceries - JIO OVERRIDES RELIANCE)
    has_telecom = (re.search(r'\bJIO\b', text_upper) or
                   re.search(r'\bAIRTEL\b', text_upper) or
                   re.search(r'\bVODAFONE\b', text_upper) or
                   re.search(r'\bVI\b', text_upper) or
                   re.search(r'\bBSNL\b', text_upper))
    
    # Also check if fuel keywords exist (if so, skip groceries)
    has_fuel = (re.search(r'\bPETROL\b', text_upper) or
                re.search(r'\bFUEL\b', text_upper) or
                re.search(r'\bBPCL\b', text_upper) or
                re.search(r'\bHPCL\b', text_upper) or
                re.search(r'\bIOCL\b', text_upper))
    
    if not has_telecom and not has_fuel and not has_utility_keyword:
        if (re.search(r'\bSPENCERS\b', text_upper) or 
            re.search(r'\bSPENCER\'?S\b', text_upper) or
            re.search(r'\bSPENCER\b', text_upper) or
            re.search(r'\bDMART\b', text_upper) or
            re.search(r'\bD\'?MART\b', text_upper) or
            re.search(r'\bBIG\s+BAZAAR\b', text_upper) or
            re.search(r'\bBIGBAZAAR\b', text_upper) or
            re.search(r'\bRELIANCE\s+SMART\b', text_upper) or
            re.search(r'\bRELIANCE\b', text_upper) or
            re.search(r'\bNATURE\'?S\s+BASKET\b', text_upper) or
            re.search(r'\bNATURE\s+S\s+BASKET\b', text_upper) or
            re.search(r'\bBIGBASKET\b', text_upper) or
            re.search(r'\bBIG\s+BASKET\b', text_upper) or
            re.search(r'\bGROFERS\b', text_upper)):
            if 8 < matched_priority:
                matched_priority = 8
                matched_category = 'groceries'
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 8: FOOD & DINING
    # ============================================================
    if (re.search(r'\bSWIGGY\b', text_upper) or 
        re.search(r'\bZOMATO\b', text_upper) or
        re.search(r'\bMCDONALD\b', text_upper) or
        re.search(r'\bMCDONALDS\b', text_upper) or
        re.search(r'\bKFC\b', text_upper) or
        re.search(r'\bBURGER\s+KING\b', text_upper) or
        re.search(r'\bBURGERKING\b', text_upper) or
        re.search(r'\bINSTAMART\b', text_upper) or
        re.search(r'\bBARBEQUE\s+NATION\b', text_upper) or
        re.search(r'\bBARBEQUE\b', text_upper) or
        re.search(r'\bMONCHUNIES\b', text_upper) or
        re.search(r'\bDOMINOS\b', text_upper) or
        re.search(r'\bDOMINO\b', text_upper) or
        re.search(r'\bPIZZA\s+HUT\b', text_upper) or
        re.search(r'\bSUBWAY\b', text_upper) or
        re.search(r'\bHALDIRAM\b', text_upper) or
        re.search(r'\bHALDIRAMS\b', text_upper)):
        if 9 < matched_priority:
            matched_priority = 9
            matched_category = 'food_dining'
            matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 9: ENTERTAINMENT
    # ============================================================
    if (re.search(r'\bPVR\b', text_upper) or
        re.search(r'\bPVR\s+CINEMAS\b', text_upper) or
        re.search(r'\bCINEPOLIS\b', text_upper) or
        re.search(r'\bBOOKMYSHOW\b', text_upper) or
        re.search(r'\bBOOK\s+MY\s+SHOW\b', text_upper) or
        re.search(r'\bINOX\b', text_upper) or
        re.search(r'\bCINEMA\b', text_upper) or
        re.search(r'\bMOVIE\b', text_upper)):
        if 10 < matched_priority:
            matched_priority = 10
            matched_category = 'entertainment'
            matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 10: SHOPPING
    # ============================================================
    if (re.search(r'\bAJIO\b', text_upper) or
        re.search(r'\bAMAZON\b', text_upper) or
        re.search(r'\bFLIPKART\b', text_upper) or
        re.search(r'\bMYNTRA\b', text_upper) or
        re.search(r'\bDMART\b', text_upper) or
        re.search(r'\bD\'?MART\b', text_upper) or
        re.search(r'\bBIG\s+BAZAAR\b', text_upper) or
        re.search(r'\bBIGBAZAAR\b', text_upper) or
        re.search(r'\bPANTALOONS\b', text_upper) or
        re.search(r'\bWESTSIDE\b', text_upper) or
        re.search(r'\bLIFESTYLE\b', text_upper) or
        re.search(r'\bSHOPPER\b', text_upper)):
        if 11 < matched_priority:
            matched_priority = 11
            matched_category = 'shopping'
            if re.search(r'\bAJIO\b', text_upper):
                matched_merchant = 'AJIO'
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 11: TRAVEL (includes FASTAG/TOLL, but travel bookings already handled at Priority 3)
    # ============================================================
    if (re.search(r'\bOLA\b', text_upper) or
        re.search(r'\bUBER\b', text_upper) or
        re.search(r'\bRAPIDO\b', text_upper) or
        re.search(r'\bIRCTC\b', text_upper) or
        re.search(r'\bGOIBIBO\b', text_upper) or
        re.search(r'\bGO\s+IBIBO\b', text_upper) or
        re.search(r'\bMETRO\b', text_upper) or
        re.search(r'\bREDBUS\b', text_upper) or
        re.search(r'\bRED\s+BUS\b', text_upper) or
        re.search(r'\bPMPML\b', text_upper) or
        re.search(r'\bPMPL\b', text_upper) or
        re.search(r'\bMAKE\s+MY\s+TRIP\b', text_upper) or
        re.search(r'\bMAKEMYTRIP\b', text_upper) or
        re.search(r'\bFASTAG\b', text_upper) or
        re.search(r'\bTOLL\b', text_upper)):
        if 11 < matched_priority:
            matched_priority = 11
            matched_category = 'travel'
            if re.search(r'\bFASTAG\b', text_upper) or re.search(r'\bTOLL\b', text_upper):
                matched_merchant = 'Fastag'
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 12: HEALTHCARE
    # ============================================================
    if (re.search(r'\bPRACTO\b', text_upper) or
        re.search(r'\bGYM\b', text_upper) or
        re.search(r'\bFITNESS\b', text_upper) or
        re.search(r'\bGOLD\'?S\s+GYM\b', text_upper) or
        re.search(r'\bGOLDS\s+GYM\b', text_upper) or
        re.search(r'\bCULT\s+FIT\b', text_upper) or
        re.search(r'\bCULTFIT\b', text_upper) or
        re.search(r'\bTALWALKARS\b', text_upper) or
        re.search(r'\bANYTIME\s+FITNESS\b', text_upper) or
        re.search(r'\bHOSPITAL\b', text_upper) or
        re.search(r'\bFORTIS\b', text_upper) or
        re.search(r'\bAPOLLO\b', text_upper) or
        re.search(r'\bPHARMACY\b', text_upper) or
        re.search(r'\bMEDICAL\b', text_upper) or
        re.search(r'\bMEDPLUS\b', text_upper) or
        re.search(r'\bMED\s+PLUS\b', text_upper)):
        if 12 < matched_priority:
            matched_priority = 12
            matched_category = 'healthcare'
            matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else None
    
    # ============================================================
    # PRIORITY 13: RENT (MUST NEVER be transfer)
    # ============================================================
    # RENT, HOUSE RENT → category = rent
    if (re.search(r'\bRENT\b', text_upper) or
        re.search(r'\bHOUSE\s+RENT\b', text_upper) or
        re.search(r'\bRENTAL\b', text_upper) or
        re.search(r'\bRENT\s+PAYMENT\b', text_upper)):
        if 13 < matched_priority:
            matched_priority = 13
            matched_category = 'rent'
            matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else 'Rent Payment'
    
    # ============================================================
    # PRIORITY 14: INSURANCE
    # ============================================================
    # IF description contains: LIC, HDFC LIFE, INSURANCE, PREMIUM, POLICY
    # THEN: category = "insurance"
    if (re.search(r'\bLIC\b', text_upper) or
        re.search(r'\bHDFC\s+LIFE\b', text_upper) or
        re.search(r'\bHDFCLIFE\b', text_upper) or
        re.search(r'\bINSURANCE\b', text_upper) or
        re.search(r'\bPREMIUM\b', text_upper) or
        re.search(r'\bPOLICY\b', text_upper) or
        re.search(r'\bLIFE\s+INSURANCE\b', text_upper) or
        re.search(r'\bHEALTH\s+INSURANCE\b', text_upper) or
        re.search(r'\bTERM\s+INSURANCE\b', text_upper)):
        if 14 < matched_priority:
            matched_priority = 14
            matched_category = 'insurance'
            # Set merchant to detected insurance brand
            if re.search(r'\bLIC\b', text_upper):
                matched_merchant = 'LIC'
            elif re.search(r'\bHDFC\s+LIFE\b', text_upper) or re.search(r'\bHDFCLIFE\b', text_upper):
                matched_merchant = 'HDFC Life'
            elif re.search(r'\bINSURANCE\b', text_upper):
                # Try to extract insurance company name (NEVER use generic "Insurance")
                insurance_match = re.search(r'\b([A-Z]+(?:\s+[A-Z]+)*)\s+(?:LIFE|HEALTH|TERM)?\s*INSURANCE\b', text_upper)
                if insurance_match:
                    company_name = insurance_match.group(1).strip()
                    # Check if it's a known insurance brand
                    if company_name.upper() in ['LIC', 'HDFC', 'ICICI', 'SBI', 'BAJAJ', 'MAX', 'STAR', 'RELIANCE']:
                        matched_merchant = company_name.title() + ' Insurance'
                    else:
                        matched_merchant = company_name.title() + ' Insurance'
                else:
                    # Try to extract from context - look for insurance company names
                    if extracted_merchant != 'Unknown':
                        matched_merchant = extracted_merchant
                    else:
                        # Last resort: try to find any company name before "INSURANCE"
                        company_match = re.search(r'([A-Z][A-Z\s&]+?)\s+INSURANCE', text_upper)
                        if company_match:
                            matched_merchant = company_match.group(1).strip().title() + ' Insurance'
                        else:
                            matched_merchant = 'LIC'  # Default to LIC as most common
            else:
                matched_merchant = extracted_merchant if extracted_merchant != 'Unknown' else 'LIC'  # Default to LIC, never generic "Insurance"
    
    # ============================================================
    # PRIORITY 15: INCOME (SALARY / CREDIT SALARY) (UNION BANK FIX: NEVER ASSUME SALARY)
    # ============================================================
    # UNION BANK FIX: Salary must be detected ONLY IF:
    # - Description contains: SALARY, PAYROLL, CREDIT SALARY, NEFT.*SALARY
    # - UPI credit from a person name is NOT salary
    
    # Check if this is a UPI/IMPS/NEFT credit from a person name (NOT salary)
    is_person_transfer = False
    if credit_amount > 0 and debit_amount == 0:
        # Check for UPIAB, UPIAR, MOBFT, IMPS, NEFT patterns with person name
        if (re.search(r'\bUPIAB\b', text_upper) or 
            re.search(r'\bUPIAR\b', text_upper) or 
            re.search(r'\bMOBFT\b', text_upper) or
            re.search(r'\bIMPS\b', text_upper) or
            re.search(r'\bNEFT\b', text_upper)):
            # Extract person name from CR/<NAME>/ or DR/<NAME>/ or UPI patterns
            person_name_found = False
            cr_name_match = re.search(r'CR/([^/]+?)(?:/|$)', text_upper)
            if cr_name_match:
                person_name = cr_name_match.group(1).strip()
                person_name = re.sub(r'@.*$', '', person_name).strip()
                # Check if it's NOT a known brand (if it's a brand, it's not a person transfer)
                is_known_brand = False
                for brand_key in KNOWN_BRANDS.keys():
                    if brand_key in person_name.upper():
                        is_known_brand = True
                        break
                if not is_known_brand and len(person_name) > 1:
                    person_name_found = True
                    is_person_transfer = True
            
            # Also check UPIAR/UPIAB patterns
            if not person_name_found:
                upi_merchant_match = re.search(r'(UPIAR|UPIAB)/[^/]+/(DR|CR)/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
                if upi_merchant_match:
                    merchant_segment = upi_merchant_match.group(3).strip()
                    merchant_segment = re.sub(r'\s+/.*$', '', merchant_segment).strip()
                    # Check if it's NOT a known brand
                    is_known_brand = False
                    for brand_key in KNOWN_BRANDS.keys():
                        if brand_key in merchant_segment.upper():
                            is_known_brand = True
                            break
                    if not is_known_brand and len(merchant_segment) > 1:
                        is_person_transfer = True
    
    # UNION BANK FIX: Salary detection - ONLY if explicit salary keywords
    is_salary = False
    if (re.search(r'\bSALARY\b', text_upper) or 
        re.search(r'\bPAYROLL\b', text_upper) or
        re.search(r'\bCREDIT\s+SALARY\b', text_upper) or
        re.search(r'\bNEFT.*SALARY\b', text_upper)):
        # ONLY mark as salary if it's NOT a person transfer
        if not is_person_transfer:
            is_salary = True
    
    if is_salary:
        if 15 < matched_priority:
            matched_priority = 15
            # Rule: If description contains "salary" AND debit > 0 → category = "bank_charges", merchant = "Bank"
            if debit_amount > 0 and credit_amount == 0:
                # This is a salary deduction (bank charges), not a salary credit
                matched_category = 'bank_charges'
                matched_merchant = 'Bank'
                matched_debit_or_credit = 'debit'
                matched_transaction_type = 'debit'
            else:
                # Salary credit (normal case)
                matched_category = 'income'
                # Extract company name BEFORE "SALARY" or use detected employer
                salary_match = re.search(r'([A-Z][A-Z\s&]+?)\s+SALARY', text_upper)
                if salary_match:
                    company_name = salary_match.group(1).strip()
                    company_name = re.sub(r'\b(FROM|FOR|MONTH|PAYMENT|CREDIT|DEBIT)\b', '', company_name).strip()
                    if len(company_name) > 2:
                        matched_merchant = company_name.title()
                    else:
                        matched_merchant = 'Salary'
                else:
                    # Check for known employer
                    for employer in KNOWN_EMPLOYERS:
                        if re.search(r'\b' + re.escape(employer.upper()) + r'\b', text_upper):
                            matched_merchant = employer.title()
                            break
                    if not matched_merchant:
                        matched_merchant = 'Salary'
                matched_debit_or_credit = 'credit'
                matched_transaction_type = 'credit'
    
    # ============================================================
    # PRIORITY 4: P2P TRANSFER (VERY STRICT - INTENT FIRST)
    # ============================================================
    # P2P TRANSFER OVERRIDE: Transfer is allowed ONLY when:
    # - Description contains UPI/IMPS/NEFT/UPIAB/UPIAR/MOBFT
    # - AND UPI contains a PERSON NAME (not @upi without known merchant)
    # - OR NEFT/IMPS with individual name
    # - AND merchant is a person name (NOT a brand)
    # - AND no brand keyword is present
    # - AND no category keyword matched above (EMI, EDUCATION, TRAVEL already handled)
    # - AND NO EMI/LOAN keywords are present (ABSOLUTE BLOCK)
    # - AND NO EDUCATION keywords are present (ABSOLUTE BLOCK)
    # - AND NO TRAVEL BOOKING keywords are present (ABSOLUTE BLOCK)
    # 
    # ❌ Brands ≠ transfer
    # ❌ Services ≠ transfer
    # If a brand merchant exists, category CANNOT be transfer.
    # UPI/IMPS/NEFT define ONLY the channel, NEVER the category.
    
    # ABSOLUTE BLOCK: If EMI/LOAN, EDUCATION, or TRAVEL BOOKING keywords exist, NEVER classify as transfer
    has_emi_loan_block = (re.search(r'\bEMI\b', text_upper) or
                          re.search(r'\bLOAN\s+EMI\b', text_upper) or
                          re.search(r'\bHOME\s+LOAN\b', text_upper) or
                          re.search(r'\bHOUSING\s+LOAN\b', text_upper) or
                          re.search(r'\bPERSONAL\s+LOAN\b', text_upper) or
                          re.search(r'\bCAR\s+LOAN\b', text_upper) or
                          re.search(r'\bEDUCATION\s+LOAN\b', text_upper) or
                          re.search(r'\bACH\s+D-\b', text_upper) or
                          re.search(r'\bHOMECRINDFIN\b', text_upper) or
                          re.search(r'\bHOME\s+CREDIT\b', text_upper) or
                          re.search(r'\bNBFC\b', text_upper) or
                          re.search(r'\bFINANCE\b', text_upper))
    
    has_education_block = (re.search(r'\bSCHOOL\b', text_upper) or
                          re.search(r'\bEDUCATION\b', text_upper) or
                          re.search(r'\bCOLLEGE\b', text_upper) or
                          re.search(r'\bUNIVERSITY\b', text_upper) or
                          re.search(r'\bTUITION\b', text_upper) or
                          re.search(r'\bFEES\b', text_upper))
    
    has_travel_booking_block = (re.search(r'\bIRCTC\b', text_upper) or
                                re.search(r'\bYATRA\b', text_upper) or
                                re.search(r'\bCLEARTRIP\b', text_upper) or
                                re.search(r'\bMAKE\s+MY\s+TRIP\b', text_upper) or
                                re.search(r'\bMAKEMYTRIP\b', text_upper) or
                                re.search(r'\bFLIGHT\b', text_upper) or
                                re.search(r'\bHOTEL\b', text_upper))
    
    # Only check transfer if:
    # 1. No category has been matched yet (matched_priority == 999)
    # 2. NO EMI/LOAN keywords are present (ABSOLUTE BLOCK)
    # 3. NO EDUCATION keywords are present (ABSOLUTE BLOCK)
    # 4. NO TRAVEL BOOKING keywords are present (ABSOLUTE BLOCK)
    if matched_priority == 999 and not has_emi_loan_block and not has_education_block and not has_travel_booking_block:
        is_transfer_channel = (re.search(r'\bUPIAB\b', text_upper) or
                               re.search(r'\bUPIAR\b', text_upper) or
                               re.search(r'\bMOBFT\b', text_upper) or
                               re.search(r'\bIMPS\b', text_upper) or
                               re.search(r'\bNEFT\b', text_upper) or
                               re.search(r'\bRTGS\b', text_upper) or
                               re.search(r'\bUPI\s+CR\b', text_upper) or
                               final_result['channel'] in ['UPI', 'IMPS', 'NEFT', 'RTGS'])
        
        # Check if any brand keyword exists (if so, NOT transfer)
        has_brand_keyword = False
        for brand_key in KNOWN_BRANDS.keys():
            if re.search(r'\b' + re.escape(brand_key) + r'\b', text_upper):
                has_brand_keyword = True
                break
        
        # Also check if extracted merchant is a known brand
        is_brand_merchant = False
        if extracted_merchant != 'Unknown':
            merchant_upper = extracted_merchant.upper()
            for brand_key in KNOWN_BRANDS.keys():
                if brand_key in merchant_upper:
                    is_brand_merchant = True
                    break
        
        # Transfer is allowed ONLY if:
        # 1. Transfer channel exists
        # 2. NO brand keyword in description
        # 3. Merchant is NOT a known brand
        # 4. Merchant is a person name (or Unknown)
        # 5. UPI contains PERSON NAME OR @upi without known merchant OR NEFT/IMPS with individual name
        if is_transfer_channel and not has_brand_keyword and not is_brand_merchant:
            if 4 < matched_priority:
                matched_priority = 4
                matched_category = 'transfer'
                matched_transaction_type = 'transfer'
                
                # Set channel
                if re.search(r'\bUPIAB\b', text_upper) or re.search(r'\bUPIAR\b', text_upper):
                    matched_channel = 'UPI'
                elif re.search(r'\bMOBFT\b', text_upper):
                    matched_channel = 'UPI'
                elif re.search(r'\bIMPS\b', text_upper):
                    matched_channel = 'IMPS'
                elif re.search(r'\bNEFT\b', text_upper):
                    matched_channel = 'NEFT'
                elif re.search(r'\bRTGS\b', text_upper):
                    matched_channel = 'RTGS'
                elif re.search(r'\bUPI\b', text_upper) or final_result['channel'] == 'UPI':
                    matched_channel = 'UPI'
                
                # Extract person name (NOT UPI handle)
                person_name = None
                
                # Pattern 1: UPIAR/<txn-id>/(DR|CR)/<MERCHANT> /<BANK>/<upi-handle>
                upiar_match = re.search(r'UPIAR/[^/]+/(DR|CR)/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
                if upiar_match:
                    merchant_segment = upiar_match.group(2).strip()
                    merchant_segment = re.sub(r'\s+/.*$', '', merchant_segment).strip()
                    # Check if it's NOT a known brand
                    is_known_brand = False
                    for brand_key in KNOWN_BRANDS.keys():
                        if brand_key in merchant_segment.upper():
                            is_known_brand = True
                            break
                    if not is_known_brand and len(merchant_segment) > 1:
                        person_name = merchant_segment
                
                # Pattern 2: UPIAB/<txn-id>/(DR|CR)/<MERCHANT> /<BANK>/<upi-handle>
                if not person_name:
                    upiab_match = re.search(r'UPIAB/[^/]+/(DR|CR)/([^/]+?)(?:\s*/[^/]+/[^/]+|$)', text_upper)
                    if upiab_match:
                        merchant_segment = upiab_match.group(2).strip()
                        merchant_segment = re.sub(r'\s+/.*$', '', merchant_segment).strip()
                        is_known_brand = False
                        for brand_key in KNOWN_BRANDS.keys():
                            if brand_key in merchant_segment.upper():
                                is_known_brand = True
                                break
                        if not is_known_brand and len(merchant_segment) > 1:
                            person_name = merchant_segment
                
                # Pattern 3: Extract from CR/<NAME>/ or DR/<NAME>/
                if not person_name:
                    cr_name_match = re.search(r'CR/([^/]+?)(?:/|$)', text_upper)
                    if cr_name_match:
                        person_name = cr_name_match.group(1).strip()
                        person_name = re.sub(r'@.*$', '', person_name).strip()
                        person_name = re.sub(r'\s+/.*$', '', person_name).strip()
                        # Check if it's a known brand
                        for brand_key in KNOWN_BRANDS.keys():
                            if brand_key in person_name.upper():
                                person_name = None
                                break
                    
                    if not person_name:
                        dr_name_match = re.search(r'DR/([^/]+?)(?:/|$)', text_upper)
                        if dr_name_match:
                            person_name = dr_name_match.group(1).strip()
                            person_name = re.sub(r'@.*$', '', person_name).strip()
                            person_name = re.sub(r'\s+/.*$', '', person_name).strip()
                            # Check if it's a known brand
                            for brand_key in KNOWN_BRANDS.keys():
                                if brand_key in person_name.upper():
                                    person_name = None
                                    break
                
                # Pattern 4: NEFT/IMPS patterns
                if not person_name:
                    neft_dr_match = re.search(r'NEFT\s+DR\s*-[^-]*-\s*([A-Z][A-Z\s]*?)(?:\s*-|$)', text_upper)
                    if neft_dr_match:
                        person_name = neft_dr_match.group(1).strip()
                        person_name = re.sub(r'\s*-.*$', '', person_name).strip()
                        person_name = re.sub(r'[^A-Z\s]', '', person_name).strip()
                    
                    if not person_name:
                        imps_match = re.search(r'IMPS\s*-[^-]*-\s*([A-Z][A-Z\s]*?)(?:\s*-|$)', text_upper)
                        if imps_match:
                            person_name = imps_match.group(1).strip()
                            person_name = re.sub(r'\s*-.*$', '', person_name).strip()
                            person_name = re.sub(r'[^A-Z\s]', '', person_name).strip()
                
                # Set merchant
                if person_name and len(person_name) > 2:
                    person_name = re.sub(r'\b(TO|FROM|FOR|PAYMENT|TRANSFER|UPI|CR|DEBIT|CREDIT|DR)\b', '', person_name).strip()
                    person_name = re.sub(r'[^A-Z\s]', '', person_name).strip()
                    if len(person_name) > 2:
                        matched_merchant = person_name.title()
                    else:
                        matched_merchant = 'Transfer'
                elif extracted_merchant != 'Unknown':
                    matched_merchant = extracted_merchant
                else:
                    matched_merchant = 'Transfer'
                
                # Set direction based on debit/credit
                if debit_amount > 0:
                    matched_transaction_type = 'transfer'
                    matched_debit_or_credit = 'debit'
                elif credit_amount > 0:
                    matched_transaction_type = 'transfer_received'
                    matched_debit_or_credit = 'credit'
    
    # ============================================================
    # PRIORITY 16: INTEREST (INTEREST OVERRIDE - IGNORE AMOUNT COLUMNS)
    # ============================================================
    # FIX 3: INTEREST OVERRIDE (IGNORE AMOUNT COLUMNS)
    # IF description contains: CREDIT INTEREST, INTEREST CREDIT, SAVINGS INTEREST
    # THEN: category = "interest_income", debit_or_credit = "credit", transaction_type = "credit"
    # Even if debit > 0 in raw data.
    if (re.search(r'\bCREDIT\s+INTEREST\b', text_upper) or 
        re.search(r'\bINTEREST\s+CREDIT\b', text_upper) or 
        re.search(r'\bINTEREST\s+INCOME\b', text_upper) or 
        re.search(r'\bINTEREST\s+PAID\b', text_upper) or
        re.search(r'\bINTEREST\s+ON\s+SAVINGS\b', text_upper) or 
        re.search(r'\bSAVINGS\s+INTEREST\b', text_upper)):
        if 16 < matched_priority:
            matched_priority = 16
            matched_category = 'interest_income'
            matched_debit_or_credit = 'credit'
            matched_transaction_type = 'credit'
    
    # ============================================================
    # PRIORITY 17: CREDIT CARD BILL PAYMENT (BILLDK + CARDS)
    # ============================================================
    # If description contains "BILLDK" AND "CARDS" → credit_card_payment
    if re.search(r'\bBILLDK\b', text_upper) and re.search(r'\bCARDS\b', text_upper):
        if 17 < matched_priority:
            matched_priority = 17
            matched_category = 'credit_card_payment'
            # Extract bank name from text if available
            bank_match = re.search(r'\b(SBI|HDFC|AXIS|ICICI|KOTAK|PNB|BOI|UNION|CENTRAL)\b', text_upper)
            if bank_match:
                bank_name = bank_match.group(1)
                matched_merchant = f'{bank_name} Credit Card'
            else:
                matched_merchant = 'Credit Card'
    
    # ============================================================
    # PRIORITY 18: CREDIT CARD PAYMENT
    # ============================================================
    if (re.search(r'\bSBI\s+CARDS\b', text_upper) or
        re.search(r'\bCARD\s+PAYMENT\b', text_upper) or
        re.search(r'\bCARD\s+SETTLEMENT\b', text_upper) or
        re.search(r'\bCARD\s+BILL\b', text_upper) or
        re.search(r'\bCREDIT\s+CARD\b', text_upper) or
        re.search(r'\bCARD\s+DUES\b', text_upper) or
        re.search(r'\bCARD\s+OUTSTANDING\b', text_upper) or
        re.search(r'\bCARD\s+STATEMENT\b', text_upper) or
        re.search(r'\bCARD\s+MINIMUM\b', text_upper) or
        re.search(r'\bCARD\s+AMOUNT\b', text_upper) or
        re.search(r'\bCARDS\s+PAYMENT\b', text_upper) or
        re.search(r'\bCC\s+PAYMENT\b', text_upper) or
        re.search(r'\bCARD\s+REPAYMENT\b', text_upper)):
        if 18 < matched_priority:
            matched_priority = 18
            matched_category = 'credit_card_payment'
    
    # ============================================================
    # STEP 3: APPLY MATCHED RESULTS (HIGHEST PRIORITY WINS)
    # ============================================================
    # Apply the highest priority match to final_result
    if matched_priority < 999:
        if matched_category:
            final_result['category'] = matched_category
        if matched_merchant:
            final_result['merchant'] = matched_merchant
        if matched_transaction_type:
            final_result['transaction_type'] = matched_transaction_type
        if matched_channel:
            final_result['channel'] = matched_channel
        if matched_debit_or_credit:
            final_result['debit_or_credit'] = matched_debit_or_credit
    
    # ============================================================
    # STEP 4: FINAL SAFETY CHECKS (RUNS AFTER ALL CATEGORY RULES)
    # ============================================================
    
    # ATM transactions MUST NEVER be shopping, groceries, food_dining, travel, or transfer
    if (re.search(r'\bATM\b', text_upper) or re.search(r'\bATW\b', text_upper)) and debit_amount > 0:
        if final_result['category'] in ['shopping', 'groceries', 'food_dining', 'travel', 'transfer']:
            final_result['category'] = 'cash'
            final_result['merchant'] = 'ATM Withdrawal'
            final_result['transaction_type'] = 'withdrawal'
            final_result['channel'] = 'ATM'
            final_result['debit_or_credit'] = 'debit'
    
    # RENT MUST NEVER be classified as transfer
    if (re.search(r'\bRENT\b', text_upper) or
        re.search(r'\bHOUSE\s+RENT\b', text_upper) or
        re.search(r'\bRENTAL\b', text_upper) or
        re.search(r'\bRENT\s+PAYMENT\b', text_upper)):
        if final_result['category'] == 'transfer':
            final_result['category'] = 'rent'
            final_result['merchant'] = extracted_merchant if extracted_merchant != 'Unknown' else 'Rent Payment'
    
    # EDUCATION MUST NEVER be classified as transfer (FINAL SAFETY CHECK)
    # Check for education keywords - must override transfer
    has_education_keyword_final = False
    education_type_final = None
    
    # Check for specific education keywords (order matters - check more specific first)
    if re.search(r'\bSCHOOL\s+FEES\b', text_upper) or re.search(r'\bSCHOOLFEES\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'SCHOOL_FEES'
    elif re.search(r'\bEDUCATION\s+FEE\b', text_upper) or re.search(r'\bEDUCATION\s+FEES\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'EDUCATION_FEE'
    elif re.search(r'\bTUITION\s+FEE\b', text_upper) or re.search(r'\bTUITION\s+FEES\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'TUITION_FEE'
    elif re.search(r'\bANNUAL\s+FEE\b', text_upper) or re.search(r'\bANNUAL\s+FEES\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'ANNUAL_FEE'
    elif re.search(r'\bSCHOOL\s+ADMISSION\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'SCHOOL_ADMISSION'
    elif re.search(r'\bSCHOOL\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'SCHOOL'
    elif re.search(r'\bCOLLEGE\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'COLLEGE'
    elif re.search(r'\bUNIVERSITY\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'UNIVERSITY'
    elif re.search(r'\bTUITION\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'TUITION'
    elif re.search(r'\bADMISSION\b', text_upper):
        has_education_keyword_final = True
        education_type_final = 'ADMISSION'
    elif re.search(r'\bFEES\b', text_upper) and (re.search(r'\bSCHOOL\b', text_upper) or re.search(r'\bEDUCATION\b', text_upper) or re.search(r'\bTUITION\b', text_upper)):
        has_education_keyword_final = True
        education_type_final = 'FEES'
    
    if has_education_keyword_final:
        if final_result['category'] in ['transfer', 'others', 'shopping']:
            final_result['category'] = 'education'
            final_result['transaction_type'] = 'expense'
            # Set merchant based on detected education keyword
            if education_type_final == 'SCHOOL_FEES':
                final_result['merchant'] = 'School Fees'
            elif education_type_final == 'EDUCATION_FEE':
                final_result['merchant'] = 'Education Fee'
            elif education_type_final == 'TUITION_FEE':
                final_result['merchant'] = 'Tuition Fee'
            elif education_type_final == 'ANNUAL_FEE':
                final_result['merchant'] = 'School Fees'
            elif education_type_final == 'SCHOOL_ADMISSION':
                final_result['merchant'] = 'School Admission'
            elif education_type_final == 'SCHOOL':
                final_result['merchant'] = 'School'
            elif education_type_final == 'COLLEGE':
                final_result['merchant'] = 'College'
            elif education_type_final == 'UNIVERSITY':
                final_result['merchant'] = 'University'
            elif education_type_final == 'TUITION':
                final_result['merchant'] = 'Tuition'
            elif education_type_final == 'ADMISSION':
                final_result['merchant'] = 'Admission'
            elif education_type_final == 'FEES':
                final_result['merchant'] = 'Fees'
            else:
                final_result['merchant'] = extracted_merchant if extracted_merchant != 'Unknown' else 'Education'
    
    # TRAVEL BOOKINGS MUST NEVER be classified as transfer (FINAL SAFETY CHECK)
    has_travel_booking_keyword_final = (re.search(r'\bIRCTC\b', text_upper) or
                                        re.search(r'\bYATRA\b', text_upper) or
                                        re.search(r'\bCLEARTRIP\b', text_upper) or
                                        re.search(r'\bMAKE\s+MY\s+TRIP\b', text_upper) or
                                        re.search(r'\bMAKEMYTRIP\b', text_upper) or
                                        re.search(r'\bFLIGHT\b', text_upper) or
                                        re.search(r'\bHOTEL\b', text_upper))
    
    if has_travel_booking_keyword_final:
        if final_result['category'] in ['transfer', 'others']:
            final_result['category'] = 'travel'
            final_result['transaction_type'] = 'expense'
            # Set merchant based on detected travel platform
            if re.search(r'\bIRCTC\b', text_upper):
                final_result['merchant'] = 'IRCTC'
            elif re.search(r'\bYATRA\b', text_upper):
                final_result['merchant'] = 'Yatra'
            elif re.search(r'\bCLEARTRIP\b', text_upper):
                final_result['merchant'] = 'Cleartrip'
            elif re.search(r'\bMAKE\s+MY\s+TRIP\b', text_upper) or re.search(r'\bMAKEMYTRIP\b', text_upper):
                final_result['merchant'] = 'MakeMyTrip'
            elif re.search(r'\bFLIGHT\b', text_upper):
                final_result['merchant'] = 'Flight Booking'
            elif re.search(r'\bHOTEL\b', text_upper):
                final_result['merchant'] = 'Hotel Booking'
            else:
                final_result['merchant'] = extracted_merchant if extracted_merchant != 'Unknown' else 'Travel Booking'
    
    # EMI / LOAN MUST NEVER be classified as transfer (FINAL SAFETY CHECK)
    # Check for loan types FIRST (more specific), then generic EMI
    has_emi_loan_keyword_final = False
    loan_type_final = None
    
    # Check for specific loan types (order matters - check more specific first)
    if re.search(r'\bHOME\s+LOAN\s+EMI\b', text_upper) or re.search(r'\bHOUSING\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'HOME_LOAN'
    elif re.search(r'\bHOME\s+LOAN\b', text_upper) or re.search(r'\bHOUSING\s+LOAN\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'HOME_LOAN'
    elif re.search(r'\bPERSONAL\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'PERSONAL_LOAN'
    elif re.search(r'\bPERSONAL\s+LOAN\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'PERSONAL_LOAN'
    elif re.search(r'\bCAR\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'CAR_LOAN'
    elif re.search(r'\bCAR\s+LOAN\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'CAR_LOAN'
    elif re.search(r'\bEDUCATION\s+LOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'EDUCATION_LOAN'
    elif re.search(r'\bEDUCATION\s+LOAN\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'EDUCATION_LOAN'
    elif re.search(r'\bLOAN\s+EMI\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'LOAN_EMI'
    elif re.search(r'\bHOMECRINDFIN\b', text_upper) or re.search(r'\bHOME\s+CREDIT\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'HOME_CREDIT'
    elif re.search(r'\bACH\s+D-\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'ACH_LOAN'
    elif re.search(r'\bNBFC\b', text_upper) or re.search(r'\bFINANCE\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'LOAN'
    elif re.search(r'\bEMI\b', text_upper):
        has_emi_loan_keyword_final = True
        loan_type_final = 'EMI'
    
    if has_emi_loan_keyword_final:
        # ABSOLUTE OVERRIDE: EMI/LOAN MUST NEVER be transfer, others, or any other category
        # This is the FINAL safety check - override ANY category if EMI keywords exist
        if final_result['category'] in ['transfer', 'shopping', 'food_dining', 'groceries', 'entertainment', 'travel', 'healthcare', 'fuel', 'bills_utilities']:
            final_result['category'] = 'emi_loan'
            final_result['transaction_type'] = 'loan_payment'
            # Set merchant based on detected loan type
            if loan_type_final == 'HOME_LOAN':
                final_result['merchant'] = 'Home Loan EMI'
            elif loan_type_final == 'PERSONAL_LOAN':
                final_result['merchant'] = 'Personal Loan EMI'
            elif loan_type_final == 'CAR_LOAN':
                final_result['merchant'] = 'Car Loan EMI'
            elif loan_type_final == 'EDUCATION_LOAN':
                final_result['merchant'] = 'Education Loan EMI'
            elif loan_type_final == 'HOME_CREDIT':
                final_result['merchant'] = 'Home Credit EMI'
            elif loan_type_final == 'LOAN_EMI':
                final_result['merchant'] = 'Loan EMI Payment'
            elif loan_type_final == 'EMI':
                final_result['merchant'] = 'EMI Payment'
            else:
                final_result['merchant'] = extracted_merchant if extracted_merchant != 'Unknown' else 'Loan EMI Payment'
    
    # UTILITIES MUST NEVER be classified as transfer or fuel (ABSOLUTE RULE)
    has_utility_keyword_final = (re.search(r'\bELECTRICITY\b', text_upper) or
                                  re.search(r'\bPOWER\b', text_upper) or
                                  re.search(r'\bDISCOM\b', text_upper) or
                                  re.search(r'\bMSEDCL\b', text_upper) or
                                  re.search(r'\bMSEB\b', text_upper) or
                                  re.search(r'\bBESCOM\b', text_upper) or
                                  re.search(r'\bTANGEDCO\b', text_upper) or
                                  re.search(r'\bGAS\s+PAYMENT\b', text_upper) or
                                  re.search(r'\bGAS\s+BILL\b', text_upper) or
                                  re.search(r'\bLPG\b', text_upper) or
                                  re.search(r'\bFIBER\b', text_upper) or
                                  re.search(r'\bBROADBAND\b', text_upper) or
                                  re.search(r'\bDTH\b', text_upper) or
                                  re.search(r'\bINTERNET\s+PAYMENT\b', text_upper) or
                                  re.search(r'\bINTERNET\b', text_upper))
    
    # Check for telecom with service words
    if (re.search(r'\bJIO\b', text_upper) or re.search(r'\bAIRTEL\b', text_upper) or 
        re.search(r'\bVI\b', text_upper) or re.search(r'\bVODAFONE\b', text_upper) or 
        re.search(r'\bBSNL\b', text_upper)):
        if (re.search(r'\bRECHARGE\b', text_upper) or re.search(r'\bBILL\b', text_upper) or
            re.search(r'\bFIBER\b', text_upper) or re.search(r'\bBROADBAND\b', text_upper) or
            re.search(r'\bDTH\b', text_upper)):
            has_utility_keyword_final = True
    
    if has_utility_keyword_final:
        if final_result['category'] in ['transfer', 'fuel']:
            final_result['category'] = 'bills_utilities'
            # Set merchant based on utility type
            if re.search(r'\bMSEDCL\b', text_upper):
                final_result['merchant'] = 'MSEDCL'
            elif re.search(r'\bMSEB\b', text_upper):
                final_result['merchant'] = 'MSEB'
            elif re.search(r'\bBESCOM\b', text_upper):
                final_result['merchant'] = 'BESCOM'
            elif re.search(r'\bTANGEDCO\b', text_upper):
                final_result['merchant'] = 'TANGEDCO'
            elif re.search(r'\bDISCOM\b', text_upper):
                final_result['merchant'] = 'DISCOM'
            elif re.search(r'\bELECTRICITY\b', text_upper) or re.search(r'\bPOWER\b', text_upper):
                final_result['merchant'] = 'Electricity'
            elif re.search(r'\bGAS\s+PAYMENT\b', text_upper) or re.search(r'\bGAS\s+BILL\b', text_upper) or re.search(r'\bLPG\b', text_upper):
                final_result['merchant'] = 'Gas'
            elif re.search(r'\bJIO\b', text_upper):
                final_result['merchant'] = 'Jio'
            elif re.search(r'\bAIRTEL\b', text_upper):
                final_result['merchant'] = 'Airtel'
            elif re.search(r'\bVI\b', text_upper):
                final_result['merchant'] = 'Vi'
            elif re.search(r'\bVODAFONE\b', text_upper):
                final_result['merchant'] = 'Vodafone'
            elif re.search(r'\bBSNL\b', text_upper):
                final_result['merchant'] = 'BSNL'
            elif re.search(r'\bINTERNET\b', text_upper):
                final_result['merchant'] = 'Internet Service'
            elif final_result['merchant'] == 'Unknown':
                final_result['merchant'] = 'Utility'
    
    # UNION BANK FIX: UPI Category Correction - Use keyword mapping FIRST, only default to transfer if no match
    # Rule: If channel == "UPI" AND merchant == "Unknown" AND no category keyword matched → merchant = "UPI Transfer", category = "transfer"
    # BUT: If a brand merchant exists, category CANNOT be transfer
    if final_result['channel'] == 'UPI':
        # Check if a category was assigned by keyword matching (from priority rules above)
        category_from_keywords = final_result.get('category', 'transfer')
        
        # Check if merchant is a known brand
        merchant_upper = final_result['merchant'].upper()
        is_brand_merchant = False
        for brand_key in KNOWN_BRANDS.keys():
            if brand_key in merchant_upper:
                is_brand_merchant = True
                break
        
        # Only set transfer if:
        # 1. Category is still 'transfer' (no keyword matched)
        # 2. Merchant is Unknown (not a brand)
        # 3. Merchant is NOT a known brand
        if category_from_keywords == 'transfer' and final_result['merchant'] == 'Unknown' and not is_brand_merchant:
            final_result['merchant'] = 'UPI Transfer'
            final_result['category'] = 'transfer'
        # If category was set by keywords (food_dining, shopping, entertainment, etc.), keep it
        # DO NOT override keyword-matched categories to transfer
    
    # Merchant must not be "Unknown" if brand exists
    if final_result['merchant'] == 'Unknown' and extracted_merchant != 'Unknown':
        final_result['merchant'] = extracted_merchant
    
    # ============================================================
    # FINAL SAFETY CHECK: Brand merchants CANNOT be transfer
    # ============================================================
    # If merchant is a known brand, category CANNOT be transfer
    if final_result['category'] == 'transfer':
        merchant_upper = final_result['merchant'].upper()
        is_brand_merchant = False
        for brand_key in KNOWN_BRANDS.keys():
            if brand_key in merchant_upper:
                is_brand_merchant = True
                # Override: Set category based on brand
                if brand_key in ['SWIGGY', 'ZOMATO', 'MCDONALD', 'KFC', 'DOMINOS', 'PIZZA HUT', 'SUBWAY', 'HALDIRAM']:
                    final_result['category'] = 'food_dining'
                elif brand_key in ['DMART', 'BIG BAZAAR', 'BIGBAZAAR', 'SPENCERS', "SPENCER'S", 'SPENCER', 'RELIANCE', 'BIGBASKET', 'GROFERS']:
                    final_result['category'] = 'groceries'
                elif brand_key in ['PVR', 'CINEPOLIS', 'BOOKMYSHOW', 'INOX', 'CINEMA', 'MOVIE']:
                    final_result['category'] = 'entertainment'
                elif brand_key in ['AJIO', 'AMAZON', 'FLIPKART', 'MYNTRA', 'PANTALOONS', 'WESTSIDE', 'LIFESTYLE']:
                    final_result['category'] = 'shopping'
                elif brand_key in ['LIC', 'HDFC LIFE', 'HDFCLIFE']:
                    final_result['category'] = 'insurance'
                break
        
        # If still transfer but merchant is a brand, try to classify based on brand
        if is_brand_merchant and final_result['category'] == 'transfer':
            # Try to classify based on brand type
            merchant_upper = final_result['merchant'].upper()
            if any(brand in merchant_upper for brand in ['SWIGGY', 'ZOMATO', 'MCDONALD', 'KFC', 'DOMINOS', 'PIZZA HUT', 'SUBWAY', 'HALDIRAM']):
                final_result['category'] = 'food_dining'
            elif any(brand in merchant_upper for brand in ['DMART', 'BIG BAZAAR', 'BIGBAZAAR', 'SPENCERS', "SPENCER'S", 'SPENCER', 'RELIANCE', 'BIGBASKET', 'GROFERS']):
                final_result['category'] = 'groceries'
            elif any(brand in merchant_upper for brand in ['PVR', 'CINEPOLIS', 'BOOKMYSHOW', 'INOX', 'CINEMA', 'MOVIE']):
                final_result['category'] = 'entertainment'
            elif any(brand in merchant_upper for brand in ['AJIO', 'AMAZON', 'FLIPKART', 'MYNTRA', 'PANTALOONS', 'WESTSIDE', 'LIFESTYLE']):
                final_result['category'] = 'shopping'
            elif any(brand in merchant_upper for brand in ['LIC', 'HDFC LIFE', 'HDFCLIFE']):
                final_result['category'] = 'insurance'
            else:
                # If we can't classify, keep as transfer but this shouldn't happen
                final_result['category'] = 'transfer'
    
    # ============================================================
    # FIX 4: DTH / BROADBAND / FIBER OVERRIDE (FINAL SAFETY CHECK)
    # ============================================================
    # DTH MUST NEVER be classified as entertainment
    if (re.search(r'\bDTH\b', text_upper) or
        re.search(r'\bFIBER\b', text_upper) or
        re.search(r'\bBROADBAND\b', text_upper) or
        re.search(r'\bAIRTEL\b', text_upper) or
        re.search(r'\bJIO\b', text_upper) or
        re.search(r'\bVI\b', text_upper) or
        re.search(r'\bBSNL\b', text_upper)):
        if final_result['category'] == 'entertainment':
            final_result['category'] = 'bills_utilities'
            # Set merchant to detected telecom brand
            if re.search(r'\bJIO\b', text_upper):
                final_result['merchant'] = 'Jio'
            elif re.search(r'\bAIRTEL\b', text_upper):
                final_result['merchant'] = 'Airtel'
            elif re.search(r'\bVODAFONE\b', text_upper):
                final_result['merchant'] = 'Vodafone'
            elif re.search(r'\bVI\b', text_upper):
                final_result['merchant'] = 'Vi'
            elif re.search(r'\bBSNL\b', text_upper):
                final_result['merchant'] = 'BSNL'
    
    # ============================================================
    # STEP 5: FINAL DEBIT / CREDIT OVERRIDE (FIX 1 - ABSOLUTE - RUNS LAST)
    # ============================================================
    # FIX 1: FINAL DEBIT / CREDIT OVERRIDE (ABSOLUTE)
    # This rule MUST run LAST and override everything
    # IGNORE OpenAI and rule-based output for this decision
    
    # MEDR transactions MUST NEVER become credit (Bank of India specific)
    if re.search(r'\bMEDR\b', text_upper):
        # MEDR transactions are ALWAYS debit - force override
        final_result['debit_or_credit'] = 'debit'
        if final_result['transaction_type'] == 'credit':
            final_result['transaction_type'] = 'debit'
        # Force credit_amount to 0 (should already be 0 from extraction, but enforce here too)
        credit_amount = 0.0
    
    # FIX 1: IF debit > 0 AND credit == 0:
    #   debit_or_credit = "debit"
    #   transaction_type MUST NOT be "credit"
    if debit_amount > 0 and credit_amount == 0:
        final_result['debit_or_credit'] = 'debit'
        # transaction_type MUST be "debit" (or specific debit type), MUST NOT be "credit"
        if final_result['transaction_type'] == 'credit':
            # Override: Determine appropriate transaction_type for debit
            if final_result['category'] == 'transfer':
                final_result['transaction_type'] = 'transfer'
            elif final_result['category'] == 'cash':
                final_result['transaction_type'] = 'withdrawal'
            elif final_result['category'] == 'bank_charges':
                final_result['transaction_type'] = 'debit'
            else:
                final_result['transaction_type'] = 'debit'
        # Ensure transaction_type is not "credit" for debits
        elif final_result['transaction_type'] not in ['debit', 'transfer', 'withdrawal']:
            final_result['transaction_type'] = 'debit'
    
    # FIX 1: IF credit > 0 AND debit == 0:
    #   debit_or_credit = "credit"
    #   transaction_type = "credit"
    elif credit_amount > 0 and debit_amount == 0:
        final_result['debit_or_credit'] = 'credit'
        final_result['transaction_type'] = 'credit'
    
    return final_result


def normalize_transaction(txn: Dict) -> Dict:
    """
    HYBRID NORMALIZATION FLOW (STRICT):
    
    STEP 1: Run rule_based_normalizer.normalize_transaction()
    → If category != "transfer" AND merchant != "Unknown" (never use "others")
    → ACCEPT RESULT (but still pass through apply_global_rules for final validation)
    
    STEP 2: ONLY IF STEP 1 RETURNS "transfer" OR "Unknown"
    → Call OpenAI normalizer to infer: merchant, category, transaction_type
    
    STEP 3: VALIDATE OpenAI OUTPUT USING GLOBAL RULES
    → Re-run ALL keyword rules on OpenAI output
    → If ANY rule contradicts OpenAI result → OVERRIDE OpenAI with rule-based
    → ATM, CASH, TRANSFER, GROCERIES, FOOD, TRAVEL RULES MUST ALWAYS WIN
    
    STEP 4: FINAL SAFETY CHECK (in apply_global_rules)
    → merchant must not be "Unknown" if brand exists
    → ATM transactions must NEVER be shopping, groceries, food_dining, travel, or transfer
    → category must not be "others" if any keyword matches
    
    STEP 5: Pass to apply_global_rules() - FINAL AUTHORITY
    → This function ALWAYS runs and ALWAYS overrides suggestions
    → Rules ALWAYS override OpenAI. NO EXCEPTIONS.
    
    STEP 6: Return final result
    """
    
    # STEP 1: Run rule_based_normalizer.normalize_transaction()
    rule_suggestion = rule_based_normalize(txn)
    
    # Check if rule-based is strong (category != "transfer" AND merchant != "Unknown")
    # Never use "others" - default to "transfer" if no classification
    rule_category = rule_suggestion.get('category', '').lower()
    if rule_category == 'others':
        rule_category = 'transfer'  # Replace "others" with "transfer"
    rule_merchant = rule_suggestion.get('merchant', '')
    
    is_rule_weak = (
        rule_category == 'transfer' or 
        rule_merchant == 'Unknown' or 
        not rule_merchant or
        rule_merchant == ''
    )
    
    # STEP 2: ONLY IF STEP 1 RETURNS "others" OR "Unknown"
    # → Call OpenAI normalizer to infer: merchant, category, transaction_type
    # OPTIMIZATION: Skip OpenAI for very simple transfers to reduce API calls and timeout
    # Only use OpenAI if description has some complexity (length > 20 chars or contains numbers/patterns)
    description = txn.get('description', '') or txn.get('narration', '')
    is_simple_transfer = (
        len(description) < 20 and 
        rule_category == 'transfer' and
        not any(char.isdigit() for char in description[:30])  # No account numbers/amounts visible
    )
    
    if is_rule_weak and not is_simple_transfer:
        try:
            if is_openai_enabled():
                openai_suggestion = normalize_transaction_with_openai(txn)
            else:
                openai_suggestion = {}  # Skip OpenAI if not available
            
            # ============================================================
            # STEP 3: VALIDATE OpenAI OUTPUT USING GLOBAL RULES
            # ============================================================
            # Get amounts from transaction
            debit_amt = float(txn.get('debit', 0) or txn.get('withdrawal', 0) or 0)
            credit_amt = float(txn.get('credit', 0) or txn.get('deposit', 0) or 0)
            
            # Prepare text for keyword validation
            narration = txn.get('narration', '') or ''
            description = txn.get('description', '') or ''
            text_upper = f"{narration} {description}".strip().upper()
            
            # VALIDATION 1: Check debit/credit columns
            # If OpenAI output conflicts with debit/credit columns → DISCARD IT
            openai_debit_or_credit = openai_suggestion.get('debit_or_credit', '').lower()
            openai_transaction_type = openai_suggestion.get('transaction_type', '').lower()
            
            violates_debit_credit_rule = False
            if debit_amt > 0 and credit_amt == 0:
                if openai_debit_or_credit == 'credit' or openai_transaction_type == 'credit':
                    violates_debit_credit_rule = True
            elif credit_amt > 0 and debit_amt == 0:
                if openai_debit_or_credit == 'debit' or openai_transaction_type == 'debit':
                    violates_debit_credit_rule = True
            
            # VALIDATION 2: Check keyword rules (ABSOLUTE PRIORITY)
            # Re-run ALL keyword rules on OpenAI output
            # If ANY rule contradicts OpenAI result → OVERRIDE OpenAI with rule-based
            openai_category = openai_suggestion.get('category', '').lower()
            violates_keyword_rule = False
            
            # ATM/CASH rule (ABSOLUTE OVERRIDE)
            if (re.search(r'\bATM\b', text_upper) or 
                re.search(r'\bATM\s+WDL\b', text_upper) or
                re.search(r'\bATM\s+CASH\b', text_upper) or
                re.search(r'\bCASH\s+WDL\b', text_upper) or
                re.search(r'\bCASH\s+WITHDRAWAL\b', text_upper)) and debit_amt > 0:
                if openai_category != 'cash':
                    violates_keyword_rule = True
            
            # FOOD & DINING keywords
            food_keywords = ['SWIGGY', 'ZOMATO', 'MCDONALD', 'KFC', 'BURGER KING', 'INSTAMART', 
                           'BARBEQUE NATION', 'MONCHUNIES', 'DOMINOS', 'SUBWAY']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in food_keywords):
                if openai_category not in ['food_dining', 'food']:
                    violates_keyword_rule = True
            
            # GROCERIES keywords
            grocery_keywords = ['DMART', 'BIG BAZAAR', 'RELIANCE SMART', 'SPENCERS', "SPENCER'S",
                              'BIGBASKET', 'GROFERS', "NATURE'S BASKET", 'NATURE S BASKET']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in grocery_keywords):
                if openai_category != 'groceries':
                    violates_keyword_rule = True
            
            # ENTERTAINMENT keywords
            entertainment_keywords = ['CINEMA', 'MOVIE', 'PVR', 'INOX', 'BOOKMYSHOW', 'CINEPOLIS']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in entertainment_keywords):
                if openai_category != 'entertainment':
                    violates_keyword_rule = True
            
            # TRAVEL keywords
            travel_keywords = ['OLA', 'UBER', 'RAPIDO', 'IRCTC', 'METRO', 'REDBUS', 'PMPML', 'MAKE MY TRIP', 'GOIBIBO']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in travel_keywords):
                if openai_category not in ['travel', 'transport']:
                    violates_keyword_rule = True
            
            # HEALTHCARE keywords
            healthcare_keywords = ['PRACTO', 'GYM', 'FITNESS', "GOLD'S GYM", 'CULT FIT', 'TALWALKARS', 
                                 'ANYTIME FITNESS', 'HOSPITAL', 'FORTIS', 'APOLLO']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in healthcare_keywords):
                if openai_category not in ['healthcare', 'health']:
                    violates_keyword_rule = True
            
            # BILLS & UTILITIES keywords
            bills_keywords = ['AIRTEL', 'JIO', 'VI', 'VODAFONE', 'BSNL', 'FIBER', 'BROADBAND', 'DTH', 'ELECTRICITY', 'GAS']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in bills_keywords):
                if openai_category not in ['bills_utilities', 'utilities', 'bills']:
                    violates_keyword_rule = True
            
            # FUEL keywords
            fuel_keywords = ['INDIAN OIL', 'IOCL', 'HP', 'HPCL', 'BPCL', 'BHARAT PETROLEUM', 'PETROL PUMP', 'SHELL']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in fuel_keywords):
                if openai_category != 'fuel':
                    violates_keyword_rule = True
            
            # TRANSFER keywords
            transfer_keywords = ['NEFT', 'IMPS', 'RTGS', 'BANK TRANSFER', 'UPI P2P']
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_upper) for kw in transfer_keywords):
                if openai_category != 'transfer':
                    violates_keyword_rule = True
            
            # If OpenAI violates ANY rule → DISCARD IT
            if violates_debit_credit_rule or violates_keyword_rule:
                # OpenAI violated rules - DISCARD IT, use rule-based
                base_suggestion = rule_suggestion
            else:
                # OpenAI is valid - normalize category format
                category_mapping = {
                    'food': 'food_dining',
                    'groceries': 'groceries',
                    'entertainment': 'entertainment',
                    'travel': 'travel',
                    'transport': 'travel',
                    'healthcare': 'healthcare',
                    'health': 'healthcare',
                    'fuel': 'fuel',
                    'utilities': 'bills_utilities',
                    'bills': 'bills_utilities',
                    'bills_utilities': 'bills_utilities',
                    'transfer': 'transfer',
                    'others': 'others',
                    'other': 'others',
                    'cash withdrawal': 'cash',
                    'cash': 'cash',
                    'shopping': 'shopping'
                }
                openai_suggestion['category'] = category_mapping.get(openai_category, openai_category)
                base_suggestion = openai_suggestion
        except Exception:
            # If OpenAI fails, use rule-based suggestion
            base_suggestion = rule_suggestion
    else:
        # Rule-based is strong, use it as suggestion
        base_suggestion = rule_suggestion
    
    # STEP 4: Prepare text for final rule engine
    narration = txn.get('narration', '').upper()
    description = txn.get('description', '').upper()
    text = f"{narration} {description}".strip()
    
    debit_amount = float(txn.get('debit', 0) or txn.get('withdrawal', 0) or 0)
    credit_amount = float(txn.get('credit', 0) or txn.get('deposit', 0) or 0)
    
    # STEP 5: Apply global rules - FINAL AUTHORITY
    # This function ALWAYS runs and ALWAYS overrides suggestions
    final_result = apply_global_rules(text, base_suggestion, debit_amount, credit_amount)
    
    # STEP 6: Return final result (NO early returns, always goes through apply_global_rules)
    return final_result
