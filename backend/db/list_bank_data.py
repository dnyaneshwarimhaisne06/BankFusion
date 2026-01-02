"""
List all bank data stored in MongoDB with details
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pymongo import MongoClient
from config import MONGO_URI, DATABASE_NAME, STATEMENTS_COLLECTION, TRANSACTIONS_COLLECTION

def list_all_bank_data():
    """List all bank statements with details"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[DATABASE_NAME]
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {str(e)}")
        return
    
    print("\n" + "="*80)
    print("BANK DATA STORED IN MONGODB")
    print("="*80)
    
    # Get all statements grouped by bank
    pipeline = [
        {
            '$group': {
                '_id': '$bankType',
                'statements': {'$push': '$$ROOT'},
                'count': {'$sum': 1}
            }
        },
        {'$sort': {'_id': 1}}
    ]
    
    bank_groups = list(db[STATEMENTS_COLLECTION].aggregate(pipeline))
    
    for bank_group in bank_groups:
        bank_type = bank_group['_id']
        statements = bank_group['statements']
        count = bank_group['count']
        
        print(f"\n{'='*80}")
        print(f"BANK: {bank_type}")
        print(f"Total Statements: {count}")
        print(f"{'='*80}")
        
        # Count transactions for this bank
        total_txns = db[TRANSACTIONS_COLLECTION].count_documents({'bankType': bank_type})
        print(f"Total Transactions: {total_txns}")
        
        print(f"\nStatements Details:")
        print("-" * 80)
        
        for idx, stmt in enumerate(statements, 1):
            stmt_id = stmt['_id']
            account_num = stmt.get('accountNumber', 'N/A')
            account_holder = stmt.get('accountHolder', 'N/A')
            branch = stmt.get('branch', 'N/A')
            total_txns_stmt = stmt.get('totalTransactions', 0)
            
            # Count actual transactions
            actual_txns = db[TRANSACTIONS_COLLECTION].count_documents({'statementId': stmt_id})
            
            print(f"\n{idx}. Statement ID: {stmt_id}")
            print(f"   Account Number: {account_num}")
            print(f"   Account Holder: {account_holder}")
            print(f"   Branch: {branch}")
            print(f"   Transactions: {actual_txns} (expected: {total_txns_stmt})")
            print(f"   Statement Period: {stmt.get('statementPeriod', 'N/A')}")
            print(f"   Created At: {stmt.get('createdAt', 'N/A')}")
    
    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    
    total_statements = db[STATEMENTS_COLLECTION].count_documents({})
    total_transactions = db[TRANSACTIONS_COLLECTION].count_documents({})
    
    print(f"Total Statements: {total_statements}")
    print(f"Total Transactions: {total_transactions}")
    
    print(f"\nBy Bank Type:")
    bank_summary = list(db[STATEMENTS_COLLECTION].aggregate([
        {'$group': {
            '_id': '$bankType',
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]))
    
    for bank in bank_summary:
        bank_type = bank['_id']
        stmt_count = bank['count']
        txn_count = db[TRANSACTIONS_COLLECTION].count_documents({'bankType': bank_type})
        print(f"  {bank_type}: {stmt_count} statements, {txn_count} transactions")

if __name__ == '__main__':
    list_all_bank_data()

