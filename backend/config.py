"""
Configuration for BankFusion Flask API
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DATABASE_NAME', 'bankfusion_db')

# Collection Names
STATEMENTS_COLLECTION = 'bank_statements'
TRANSACTIONS_COLLECTION = 'bank_transactions'

# Supported Bank Types
BANK_TYPES = ['SBI', 'HDFC', 'BOI', 'CBI', 'UNION', 'AXIS']

# Flask Configuration
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('FLASK_PORT', 5000))

