
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hybrid_normalizer import apply_global_rules

def test_rules():
    test_cases = [
        {
            "description": "IMPS-PAYTM-FASTAG*",
            "expected_category": "travel",
            "name": "FASTAG Case 1"
        },
        {
            "description": "POS PURCHASE-RAILWAY TICKET*",
            "expected_category": "travel",
            "name": "RAILWAY Case 1"
        },
        {
            "description": "IRCTC RAILWAY BOOKING",
            "expected_category": "travel",
            "name": "RAILWAY Case 2"
        },
        {
            "description": "NETC FASTAG RECHARGE",
            "expected_category": "travel",
            "name": "FASTAG Case 2"
        },
        # Regression check
        {
            "description": "UPI-NETFLIX-SUBSCRIPTION",
            "expected_category": "entertainment",
            "name": "Netflix Check"
        },
        {
            "description": "STARBUCKS COFFEE",
            "expected_category": "food_dining",
            "name": "Starbucks Check"
        }
    ]

    failed = False
    for case in test_cases:
        desc = case["description"]
        # Mock suggested result
        suggested = {
            'transaction_type': 'debit',
            'merchant': 'Unknown',
            'channel': 'UPI',
            'debit_or_credit': 'debit',
            'category': 'transfer' # Default that we want to override
        }
        
        result = apply_global_rules(desc, suggested, 100.0)
        
        if result['category'] != case['expected_category']:
            print(f"FAILED: {case['name']}")
            print(f"  Input: {desc}")
            print(f"  Expected: {case['expected_category']}")
            print(f"  Got: {result['category']}")
            failed = True
        else:
            print(f"PASSED: {case['name']} -> {result['category']}")

    if failed:
        sys.exit(1)
    else:
        print("\nAll transport rule tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    test_rules()
