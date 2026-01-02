"""
Query Bank Statements and Transactions from MongoDB
"""

import sys
from pathlib import Path
from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI, DATABASE_NAME, STATEMENTS_COLLECTION, TRANSACTIONS_COLLECTION

def connect_db():
    """Connect to MongoDB"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        return client[DATABASE_NAME]
    except Exception as e:
        print(f"✗ MongoDB connection failed: {str(e)}")
        return None

def get_statements_by_bank(bank_type: str = None):
    """Get all statements, optionally filtered by bank type"""
    db = connect_db()
    if db is None:
        return []
    
    query = {}
    if bank_type:
        query['bankType'] = bank_type.upper()
    
    statements = list(db[STATEMENTS_COLLECTION].find(query))
    return statements

def get_transactions_by_statement(statement_id: str, limit: int = 300):
    """Get transactions for a specific statement"""
    db = connect_db()
    if db is None:
        return []
    
    from bson import ObjectId
    transactions = list(db[TRANSACTIONS_COLLECTION].find(
        {'statementId': ObjectId(statement_id)}
    ).limit(limit))
    
    return transactions

def verify_anti_mixing():
    """Verify anti-mixing rules"""
    db = connect_db()
    if db is None:
        return
    
    print("\n[VERIFY] Verifying Anti-Mixing Rules...")
    print("="*70)
    
    statements = list(db[STATEMENTS_COLLECTION].find({}))
    
    issues = []
    for stmt in statements:
        stmt_id = stmt['_id']
        stmt_bank = stmt['bankType']
        
        # Get transactions
        transactions = list(db[TRANSACTIONS_COLLECTION].find({'statementId': stmt_id}))
        
        # Check bank type matching
        txn_banks = set(txn['bankType'] for txn in transactions)
        if len(txn_banks) > 1:
            issues.append(f"Statement {stmt_id}: Multiple bank types in transactions: {txn_banks}")
        elif txn_banks and list(txn_banks)[0] != stmt_bank:
            issues.append(f"Statement {stmt_id}: Bank type mismatch (stmt: {stmt_bank}, txns: {list(txn_banks)[0]})")
        
        # Check count
        if len(transactions) != 300:
            issues.append(f"Statement {stmt_id}: Expected 300 transactions, found {len(transactions)}")
    
    if issues:
        print("[ERROR] Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("[OK] All statements pass anti-mixing verification!")
    
    print(f"\nTotal statements: {len(statements)}")
    print(f"Total transactions: {db[TRANSACTIONS_COLLECTION].count_documents({})}")

def get_summary_by_bank():
    """Get summary statistics by bank"""
    db = connect_db()
    if db is None:
        return
    
    print("\n[SUMMARY] Summary by Bank Type")
    print("="*70)
    
    pipeline = [
        {
            '$group': {
                '_id': '$bankType',
                'statements': {'$sum': 1},
                'transactions': {'$sum': 1}
            }
        },
        {'$sort': {'_id': 1}}
    ]
    
    # Statement summary
    stmt_summary = list(db[STATEMENTS_COLLECTION].aggregate([
        {'$group': {
            '_id': '$bankType',
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]))
    
    # Transaction summary
    txn_summary = list(db[TRANSACTIONS_COLLECTION].aggregate([
        {'$group': {
            '_id': '$bankType',
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]))
    
    print("\nStatements:")
    for item in stmt_summary:
        print(f"  {item['_id']}: {item['count']} statement(s)")
    
    print("\nTransactions:")
    for item in txn_summary:
        print(f"  {item['_id']}: {item['count']} transaction(s)")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query bank statements and transactions')
    parser.add_argument('--verify', action='store_true', help='Verify anti-mixing rules')
    parser.add_argument('--summary', action='store_true', help='Show summary by bank')
    parser.add_argument('--bank', type=str, help='Filter by bank type (SBI, HDFC, etc.)')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_anti_mixing()
    elif args.summary:
        get_summary_by_bank()
    elif args.bank:
        statements = get_statements_by_bank(args.bank)
        print(f"\nFound {len(statements)} statement(s) for {args.bank}")
        for stmt in statements:
            print(f"  Statement ID: {stmt['_id']}")
            print(f"  Account: {stmt.get('accountNumber', 'N/A')}")
            print(f"  Holder: {stmt.get('accountHolder', 'N/A')}")
            print(f"  Transactions: {stmt.get('totalTransactions', 0)}")
            print()
    else:
        # Default: show summary
        get_summary_by_bank()
        verify_anti_mixing()

if __name__ == '__main__':
    main()

