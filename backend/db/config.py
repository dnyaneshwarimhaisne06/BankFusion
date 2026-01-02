"""
MongoDB Configuration
"""

import os

# MongoDB Connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'bankfusion_db')

# Collections
STATEMENTS_COLLECTION = 'bank_statements'
TRANSACTIONS_COLLECTION = 'bank_transactions'

# Bank Types
BANK_TYPES = ['SBI', 'HDFC', 'BOI', 'CBI', 'UNION', 'AXIS']

