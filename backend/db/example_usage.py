"""
Example: How to query bank statements and transactions from MongoDB
"""

from pymongo import MongoClient
from bson import ObjectId
from config import MONGO_URI, DATABASE_NAME, STATEMENTS_COLLECTION, TRANSACTIONS_COLLECTION

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

# Example 1: Get all statements for a specific bank
print("Example 1: Get all SBI statements")
sbi_statements = list(db[STATEMENTS_COLLECTION].find({'bankType': 'SBI'}))
print(f"Found {len(sbi_statements)} SBI statement(s)\n")

# Example 2: Get transactions for a specific statement
if sbi_statements:
    statement_id = sbi_statements[0]['_id']
    print(f"Example 2: Get transactions for statement {statement_id}")
    transactions = list(db[TRANSACTIONS_COLLECTION].find(
        {'statementId': statement_id}
    ).limit(10))
    print(f"Found {len(transactions)} transaction(s) (showing first 10)\n")
    
    for txn in transactions[:3]:
        print(f"  Date: {txn['date']}")
        print(f"  Amount: ₹{txn['amount']} ({txn['direction']})")
        print(f"  Merchant: {txn['merchant']}")
        print(f"  Category: {txn['category']}")
        print(f"  Channel: {txn['channel']}")
        print()

# Example 3: Aggregate transactions by category
print("Example 3: Transaction summary by category")
pipeline = [
    {'$group': {
        '_id': '$category',
        'count': {'$sum': 1},
        'totalAmount': {'$sum': '$amount'}
    }},
    {'$sort': {'count': -1}},
    {'$limit': 10}
]
category_summary = list(db[TRANSACTIONS_COLLECTION].aggregate(pipeline))
for item in category_summary:
    print(f"  {item['_id']}: {item['count']} transactions, ₹{item['totalAmount']:,.2f}")

# Example 4: Get transactions by merchant
print("\nExample 4: Top merchants by transaction count")
merchant_pipeline = [
    {'$group': {
        '_id': '$merchant',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
    {'$limit': 10}
]
merchant_summary = list(db[TRANSACTIONS_COLLECTION].aggregate(merchant_pipeline))
for item in merchant_summary:
    print(f"  {item['_id']}: {item['count']} transactions")

# Example 5: Verify statement-transaction linkage
print("\nExample 5: Verify statement-transaction linkage")
statements = list(db[STATEMENTS_COLLECTION].find({}).limit(5))
for stmt in statements:
    stmt_id = stmt['_id']
    txn_count = db[TRANSACTIONS_COLLECTION].count_documents({'statementId': stmt_id})
    print(f"  Statement {stmt_id} ({stmt['bankType']}): {txn_count} transactions")

