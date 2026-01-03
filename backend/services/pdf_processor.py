"""
PDF Processing Service
Handles PDF upload, extraction, normalization, and MongoDB storage
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from werkzeug.utils import secure_filename
import logging

from pdf_extractor import extract_account_info, extract_transactions
from hybrid_normalizer import normalize_transaction
from db.schema import (
    create_bank_statement_doc,
    create_transaction_doc,
    BANK_TYPES
)
from db.mongo import MongoDB
from config import STATEMENTS_COLLECTION, TRANSACTIONS_COLLECTION
from datetime import datetime

logger = logging.getLogger(__name__)

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

def detect_bank_type_from_name(bank_name: str, file_path: str = None) -> str:
    """Detect bank type from bank name"""
    if not bank_name:
        return 'SBI'  # Default fallback
    
    bank_name_upper = bank_name.upper()
    
    # Check bank name
    for key, value in BANK_NAME_MAP.items():
        if key.upper() in bank_name_upper:
            return value
    
    # Check file path if provided
    if file_path:
        path_upper = str(file_path).upper()
        for key, value in BANK_NAME_MAP.items():
            if key.upper() in path_upper:
                return value
    
    return 'SBI'  # Default fallback

class PDFProcessor:
    """Service for processing PDF uploads"""
    
    @staticmethod
    def validate_pdf_file(file) -> tuple:
        """Validate uploaded file is PDF"""
        if not file:
            return False, "No file provided"
        
        if file.filename == '':
            return False, "Empty filename"
        
        # Check extension
        allowed_extensions = {'pdf'}
        if '.' not in file.filename:
            return False, "File has no extension"
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            return False, f"Invalid file type. Only PDF files are allowed. Got: {ext}"
        
        return True, None
    
    @staticmethod
    def save_uploaded_file(file, upload_folder: str) -> str:
        """Save uploaded file to temporary location"""
        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Save file
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        return file_path
    
    @staticmethod
    def process_pdf_to_mongodb(pdf_path: str) -> Dict[str, Any]:
        """
        Process PDF: Extract → Normalize → Store in MongoDB
        Returns statement ID and processing results
        """
        db = MongoDB.get_db()
        statements_col = db[STATEMENTS_COLLECTION]
        transactions_col = db[TRANSACTIONS_COLLECTION]
        
        try:
            # Step 1: Extract account info and transactions
            logger.info(f"Extracting data from PDF: {pdf_path}")
            account_info = extract_account_info(pdf_path)
            transactions = extract_transactions(pdf_path)
            
            if not transactions:
                raise ValueError("No transactions found in PDF")
            
            # Step 2: Detect bank type
            bank_name = account_info.get('bank_name', '')
            bank_type = detect_bank_type_from_name(bank_name, pdf_path)
            
            logger.info(f"Detected bank: {bank_type} (from: {bank_name})")
            
            # Step 3: Normalize transactions
            logger.info(f"Normalizing {len(transactions)} transactions...")
            normalized_transactions = []
            
            for txn in transactions:
                try:
                    normalized = normalize_transaction(txn)
                    normalized_transactions.append({
                        'original': txn,
                        'normalized': normalized
                    })
                except Exception as e:
                    logger.warning(f"Failed to normalize transaction: {str(e)}")
                    # Continue with next transaction
                    continue
            
            if not normalized_transactions:
                raise ValueError("No valid normalized transactions")
            
            # Step 4: Create metadata
            metadata = {
                'generated_at': datetime.now().isoformat(),
                'total_transactions': len(normalized_transactions),
                'bank_name': bank_name,
                'normalization_method': 'hybrid'
            }
            
            # Step 5: Create statement document
            statement_doc = create_bank_statement_doc(
                bank_type,
                account_info,
                metadata,
                bank_specific=None
            )
            
            # Add fileName from PDF path
            statement_doc['fileName'] = os.path.basename(pdf_path)
            statement_doc['uploadDate'] = datetime.now().isoformat()
            
            # Step 6: Insert statement (parent)
            result = statements_col.insert_one(statement_doc)
            statement_id = result.inserted_id
            
            logger.info(f"Statement inserted: {statement_id}")
            
            # Step 7: Insert transactions (normalized, limit to 300)
            transaction_docs = []
            inserted_count = 0
            
            for idx, txn_data in enumerate(normalized_transactions[:300], 1):
                original = txn_data.get('original', {})
                normalized = txn_data.get('normalized', {})
                
                # Create normalized transaction document
                txn_doc = create_transaction_doc(
                    statement_id,
                    bank_type,
                    original,
                    normalized
                )
                transaction_docs.append(txn_doc)
                
                # Batch insert every 50 transactions
                if idx % 50 == 0:
                    transactions_col.insert_many(transaction_docs)
                    inserted_count += len(transaction_docs)
                    transaction_docs = []
                    logger.info(f"Progress: {idx}/{min(len(normalized_transactions), 300)} transactions")
            
            # Insert remaining transactions
            if transaction_docs:
                transactions_col.insert_many(transaction_docs)
                inserted_count += len(transaction_docs)
            
            logger.info(f"Transactions inserted: {inserted_count}")
            
            return {
                'success': True,
                'statementId': str(statement_id),
                'bankType': bank_type,
                'accountNumber': account_info.get('account_number'),
                'accountHolder': account_info.get('account_holder'),
                'transactionsInserted': inserted_count,
                'totalTransactions': len(normalized_transactions)
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

