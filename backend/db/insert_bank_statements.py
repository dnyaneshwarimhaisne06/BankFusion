"""
MongoDB Insertion Script for Bank Statements
Polymorphic Parent + Normalized Transactions Model
"""

import json
import os
from pathlib import Path
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from schema import (
    create_bank_statement_doc,
    create_transaction_doc,
    BANK_TYPES,
    normalize_date
)

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'bankfusion_db')
STATEMENTS_COLLECTION = 'bank_statements'
TRANSACTIONS_COLLECTION = 'bank_transactions'

# Bank name to bank type mapping
BANK_NAME_MAP = {
    'State Bank of India': 'SBI',
    'SBI': 'SBI',
    'HDFC Bank': 'HDFC',
    'HDFC': 'HDFC',
    'Bank of India': 'BOI',
    'BOI': 'BOI',
    'Central Bank of India': 'CBI',
    'Central Bank': 'CBI',
    'CBI': 'CBI',
    'Union Bank of India': 'UNION',
    'Union Bank': 'UNION',
    'UNION': 'UNION',
    'Axis Bank': 'AXIS',
    'AXIS': 'AXIS'
}

def detect_bank_type(bank_name: str, file_path: str) -> str:
    """Detect bank type from bank name or file path"""
    if not bank_name:
        bank_name = ''
    
    bank_name_upper = bank_name.upper()
    
    # First, check file path (folder names are more reliable)
    path_upper = str(file_path).upper()
    path_lower = str(file_path).lower()
    
    # Check for folder names in path (most reliable)
    if '\\CENTRAL\\' in path_upper or '/CENTRAL/' in path_upper or '\\CENTRAL' in path_upper or '/CENTRAL' in path_upper:
        return 'CBI'
    if '\\UNION\\' in path_upper or '/UNION/' in path_upper or '\\UNION' in path_upper or '/UNION' in path_upper:
        return 'UNION'
    if '\\UNION\\' in path_lower or '/UNION/' in path_lower or '\\UNION' in path_lower or '/UNION' in path_lower:
        return 'UNION'
    
    # Check file name for UNION or CENTRAL
    if 'UNION' in path_upper and 'STATEMENT' in path_upper:
        return 'UNION'
    if 'CENTRAL' in path_upper and 'STATEMENT' in path_upper:
        return 'CBI'
    
    # Check bank name from metadata
    for key, value in BANK_NAME_MAP.items():
        if key.upper() in bank_name_upper:
            return value
    
    # Check file path for other banks
    for key, value in BANK_NAME_MAP.items():
        if key.upper() in path_upper:
            return value
    
    # Default fallback
    return 'SBI'

def extract_bank_specific_data(bank_type: str, account_data: Dict, metadata: Dict) -> Dict:
    """Extract bank-specific fields"""
    bank_specific = {}
    
    # Add any bank-specific fields here
    # Example: if bank_type == 'SBI':
    #     bank_specific['sbi_specific_field'] = account_data.get('some_field')
    
    return bank_specific if bank_specific else None

def process_json_file(file_path: str, client: MongoClient) -> Dict[str, Any]:
    """Process a single JSON file and insert into MongoDB"""
    db = client[DATABASE_NAME]
    statements_col = db[STATEMENTS_COLLECTION]
    transactions_col = db[TRANSACTIONS_COLLECTION]
    
    print(f"\n[FILE] Processing: {Path(file_path).name}")
    
    # Read JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract data
    metadata = data.get('metadata', {})
    account_data = data.get('account', {})
    transactions = data.get('transactions', [])
    
    # Detect bank type
    bank_name = metadata.get('bank_name', '')
    bank_type = detect_bank_type(bank_name, file_path)
    
    print(f"   Bank Type: {bank_type}")
    print(f"   Transactions: {len(transactions)}")
    
    # Extract bank-specific data
    bank_specific = extract_bank_specific_data(bank_type, account_data, metadata)
    
    # Create statement document
    statement_doc = create_bank_statement_doc(bank_type, account_data, metadata, bank_specific)
    
    # Insert statement (parent)
    result = statements_col.insert_one(statement_doc)
    statement_id = result.inserted_id
    
    print(f"   [OK] Statement inserted: {statement_id}")
    
    # Insert transactions (normalized)
    transaction_docs = []
    inserted_count = 0
    
    for idx, txn in enumerate(transactions[:300], 1):  # Limit to 300
        original = txn.get('original', {})
        normalized = txn.get('normalized', {})
        
        # Create normalized transaction document
        txn_doc = create_transaction_doc(statement_id, bank_type, original, normalized)
        transaction_docs.append(txn_doc)
        
        if idx % 50 == 0:
            # Batch insert every 50 transactions
            transactions_col.insert_many(transaction_docs)
            inserted_count += len(transaction_docs)
            transaction_docs = []
            print(f"   Progress: {idx}/{min(len(transactions), 300)} transactions")
    
    # Insert remaining transactions
    if transaction_docs:
        transactions_col.insert_many(transaction_docs)
        inserted_count += len(transaction_docs)
    
    print(f"   [OK] Transactions inserted: {inserted_count}")
    
    return {
        'statementId': str(statement_id),
        'bankType': bank_type,
        'transactionsInserted': inserted_count
    }

def process_directory(directory_path: str, client: MongoClient) -> List[Dict]:
    """Process all JSON files in a directory"""
    results = []
    json_files = list(Path(directory_path).rglob('*.json'))
    
    print(f"\n[SCAN] Found {len(json_files)} JSON files")
    
    for json_file in json_files:
        try:
            result = process_json_file(str(json_file), client)
            results.append(result)
        except Exception as e:
            print(f"   [ERROR] Error processing {json_file.name}: {str(e)}")
            continue
    
    return results

def main():
    """Main function"""
    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Test connection
        print(f"[OK] Connected to MongoDB: {MONGO_URI}")
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {str(e)}")
        return
    
    db = client[DATABASE_NAME]
    
    # Get input directory
    project_root = Path(__file__).parent.parent.parent
    json_dir = project_root / 'data' / 'normalized_json'
    
    if not json_dir.exists():
        print(f"[ERROR] Directory not found: {json_dir}")
        return
    
    print(f"\n[DIR] Processing directory: {json_dir}")
    
    # Process all JSON files
    results = process_directory(str(json_dir), client)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total files processed: {len(results)}")
    
    # Count by bank
    bank_counts = {}
    total_transactions = 0
    
    for result in results:
        bank = result['bankType']
        bank_counts[bank] = bank_counts.get(bank, 0) + 1
        total_transactions += result['transactionsInserted']
    
    print(f"\nBy Bank Type:")
    for bank, count in sorted(bank_counts.items()):
        print(f"  {bank}: {count} statement(s)")
    
    print(f"\nTotal transactions inserted: {total_transactions}")
    print(f"\n[OK] Insertion complete!")
    
    # Verify anti-mixing
    print(f"\n[VERIFY] Verifying anti-mixing rules...")
    statements = list(db[STATEMENTS_COLLECTION].find({}))
    for stmt in statements:
        stmt_id = stmt['_id']
        stmt_bank = stmt['bankType']
        txn_count = db[TRANSACTIONS_COLLECTION].count_documents({'statementId': stmt_id})
        txn_banks = db[TRANSACTIONS_COLLECTION].distinct('bankType', {'statementId': stmt_id})
        
        if len(txn_banks) > 1 or (txn_banks and txn_banks[0] != stmt_bank):
            print(f"  [ERROR] MIXING DETECTED: Statement {stmt_id} has mismatched bank types!")
        else:
            print(f"  [OK] Statement {stmt_id} ({stmt_bank}): {txn_count} transactions, all {txn_banks[0] if txn_banks else 'N/A'}")

if __name__ == '__main__':
    main()

