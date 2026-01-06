
import sys
import os
import re

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hybrid_normalizer import apply_global_rules

# Handle loading pdf_extractor.py which conflicts with pdf_extractor/ directory
import importlib.util
pdf_extractor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf_extractor.py')
spec = importlib.util.spec_from_file_location("pdf_extractor_file", pdf_extractor_path)
pdf_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf_extractor_module)
detect_bank = pdf_extractor_module.detect_bank

def test_categorization_rules():
    print("Testing Categorization Rules...")
    test_cases = [
        # Groceries
        {"desc": "POS PURCHASE AT MORE STORE", "exp": "groceries"},
        {"desc": "UPI-PAYMENT-MORE SUPERMARKET", "exp": "groceries"},
        {"desc": "PURCHASE AT MORE", "exp": "groceries"},
        
        # Utilities (Jio)
        {"desc": "RELIANCE JIO RECHARGE", "exp": "bills_utilities"},
        {"desc": "UPI-JIO-PREPAID", "exp": "bills_utilities"},
        
        # Travel
        {"desc": "IRCTC BOOKING", "exp": "travel"},
        {"desc": "FASTAG RECHARGE", "exp": "travel"},
        
        # Healthcare
        {"desc": "APOLLO PHARMACY", "exp": "healthcare"},
        {"desc": "FORTIS HOSPITAL BILL", "exp": "healthcare"},
        {"desc": "1MG TECHNOLOGIES", "exp": "healthcare"},
        {"desc": "PAYMENT TO MEDPLUS", "exp": "healthcare"},
        
        # Education
        {"desc": "DPS SCHOOL FEES", "exp": "education"},
        {"desc": "COLLEGE ADMISSION FEE", "exp": "education"},
        
        # Utilities (Electricity/ISP)
        {"desc": "BESCOM BILL PAYMENT", "exp": "bills_utilities"},
        {"desc": "ACT HATHWAY INTERNET", "exp": "bills_utilities"},
        
        # Bank Charges
        {"desc": "SMS CHARGES FOR Q3", "exp": "bank_charges"},
        {"desc": "ANNUAL CHARGES DEBIT CARD", "exp": "bank_charges"},
        
        # New Rules (Kirana, Book Store, Salon, YouTube)
        {"desc": "PAYMENT TO LOCAL KIRANA STORE", "exp": "groceries"},
        {"desc": "PURCHASE AT LOCAL KIRANA", "exp": "groceries"},
        {"desc": "CITY BOOK STORE", "exp": "education"},
        {"desc": "BOOK STORE PAYMENT", "exp": "education"},
        {"desc": "LOOKS SALON", "exp": "healthcare"},
        {"desc": "SALON SERVICES", "exp": "healthcare"},
        {"desc": "YOUTUBE PREMIUM SUBSCRIPTION", "exp": "entertainment"},
        {"desc": "YOUTUBE PREMIUM", "exp": "entertainment"},
    ]
    
    failed = False
    for case in test_cases:
        desc = case["desc"]
        # Mock suggested result
        suggested = {
            'transaction_type': 'debit',
            'merchant': 'Unknown',
            'channel': 'UPI',
            'debit_or_credit': 'debit',
            'category': 'transfer' # Default that we want to override
        }
        
        result = apply_global_rules(desc, suggested, 100.0)
        
        if result['category'] != case['exp']:
            print(f"FAILED: '{desc}' -> Expected {case['exp']}, Got {result['category']}")
            failed = True
        else:
            print(f"PASSED: '{desc}' -> {result['category']}")
            
    return not failed

def test_bank_detection():
    print("\nTesting Bank Detection...")
    test_cases_bank = [
        # Union Bank
        {"text": "UNION BANK OF INDIA STATEMENT", "exp": "Union Bank of India"},
        {"text": "WELCOME TO UNION BANK", "exp": "Union Bank of India"},
        {"text": "UNION BANK OF INDIA UBIN053000", "exp": "Union Bank of India"},
        
        # Central Bank
        {"text": "CENTRAL BANK OF INDIA ACCOUNT", "exp": "Central Bank of India"},
        {"text": "CENTRAL BANK STATEMENT", "exp": "Central Bank of India"},
        {"text": "CBIN0280001", "exp": "Central Bank of India"},
        {"text": "SOME TEXT WITH CBIN CODE", "exp": "Central Bank of India"},
        
        # Multiline/Malformed Header Tests (User Reported Issue)
        {"text": "CENTRAL BANK\nOF INDIA", "exp": "Central Bank of India"},
        {"text": "CENTRAL BANK\n of India", "exp": "Central Bank of India"},
        {"text": "CENTRAL  BANK  OF  INDIA", "exp": "Central Bank of India"},
        
        # Substring Collision Tests (CRITICAL)
        {"text": "UNION BANK OF INDIA - BOI BRANCH", "exp": "Union Bank of India"},
        {"text": "CENTRAL BANK OF INDIA - BOI BRANCH", "exp": "Central Bank of India"},
        {"text": "UNION BANK OF INDIA (NOT BANK OF INDIA)", "exp": "Union Bank of India"},
        {"text": "CENTRAL BANK OF INDIA (NOT BANK OF INDIA)", "exp": "Central Bank of India"},
        
        # Negative Tests (should NOT be BOI)
        {"text": "UNION BANK OF INDIA", "not_exp": "Bank of India"},
        {"text": "CENTRAL BANK OF INDIA", "not_exp": "Bank of India"},
        {"text": "UBIN053000", "not_exp": "Bank of India"},
        {"text": "CBIN0280001", "not_exp": "Bank of India"},
        
        # BOI Tests (only if no other rules match)
        {"text": "BANK OF INDIA", "exp": "Bank of India"},
        {"text": "BOI", "exp": "Bank of India"},
    ]
    
    failed = False
    for case in test_cases_bank:
        text = case["text"]
        result = detect_bank(text)
        
        if "exp" in case:
            if result != case["exp"]:
                print(f"FAILED: '{text}' -> Expected {case['exp']}, Got {result}")
                failed = True
            else:
                print(f"PASSED: '{text}' -> {result}")
        elif "not_exp" in case:
            if result == case["not_exp"]:
                print(f"FAILED: '{text}' -> Should NOT be {case['not_exp']}, Got {result}")
                failed = True
            else:
                print(f"PASSED: '{text}' -> Not {case['not_exp']} ({result})")
                
    return not failed

if __name__ == "__main__":
    cat_success = test_categorization_rules()
    bank_success = test_bank_detection()
    
    if cat_success and bank_success:
        print("\nAll tests passed successfully!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)
