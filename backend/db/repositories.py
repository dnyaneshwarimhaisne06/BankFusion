"""
Data Access Layer - MongoDB Repositories
"""

from bson import ObjectId
from bson.errors import InvalidId
from typing import List, Dict, Optional
from db.mongo import MongoDB
from config import STATEMENTS_COLLECTION, TRANSACTIONS_COLLECTION
import logging

logger = logging.getLogger(__name__)

class StatementRepository:
    """Repository for bank_statements collection"""
    
    @staticmethod
    def get_all(bank_type: Optional[str] = None) -> List[Dict]:
        """Get all statements, optionally filtered by bank type"""
        db = MongoDB.get_db()
        collection = db[STATEMENTS_COLLECTION]
        
        query = {}
        if bank_type:
            query['bankType'] = bank_type.upper()
        
        try:
            statements = list(collection.find(query).sort('createdAt', -1))
            return statements
        except Exception as e:
            logger.error(f"Error fetching statements: {str(e)}")
            raise
    
    @staticmethod
    def get_by_id(statement_id: str) -> Optional[Dict]:
        """Get statement by ID"""
        try:
            obj_id = ObjectId(statement_id)
        except InvalidId:
            raise ValueError(f"Invalid statement ID: {statement_id}")
        
        db = MongoDB.get_db()
        collection = db[STATEMENTS_COLLECTION]
        
        try:
            statement = collection.find_one({'_id': obj_id})
            return statement
        except Exception as e:
            logger.error(f"Error fetching statement {statement_id}: {str(e)}")
            raise
    
    @staticmethod
    def exists(statement_id: str) -> bool:
        """Check if statement exists"""
        try:
            obj_id = ObjectId(statement_id)
        except InvalidId:
            return False
        
        db = MongoDB.get_db()
        collection = db[STATEMENTS_COLLECTION]
        
        return collection.count_documents({'_id': obj_id}) > 0

class TransactionRepository:
    """Repository for bank_transactions collection"""
    
    @staticmethod
    def get_by_statement_id(statement_id: str, limit: int = 1000) -> List[Dict]:
        """Get transactions for a specific statement"""
        try:
            obj_id = ObjectId(statement_id)
        except InvalidId:
            raise ValueError(f"Invalid statement ID: {statement_id}")
        
        db = MongoDB.get_db()
        collection = db[TRANSACTIONS_COLLECTION]
        
        try:
            transactions = list(
                collection.find({'statementId': obj_id})
                .sort('date', 1)
                .limit(limit)
            )
            return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions for statement {statement_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_by_bank_type(bank_type: str, limit: int = 1000) -> List[Dict]:
        """Get transactions by bank type"""
        db = MongoDB.get_db()
        collection = db[TRANSACTIONS_COLLECTION]
        
        try:
            transactions = list(
                collection.find({'bankType': bank_type.upper()})
                .sort('date', -1)
                .limit(limit)
            )
            return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions for bank {bank_type}: {str(e)}")
            raise
    
    @staticmethod
    def get_category_spend(bank_type: Optional[str] = None) -> List[Dict]:
        """Get category-wise spend (debit transactions only)"""
        db = MongoDB.get_db()
        collection = db[TRANSACTIONS_COLLECTION]
        
        # Match stage: only debit transactions
        match_stage = {'direction': 'debit'}
        if bank_type:
            match_stage['bankType'] = bank_type.upper()
        
        pipeline = [
            {'$match': match_stage},
            {
                '$group': {
                    '_id': '$category',
                    'totalAmount': {'$sum': '$amount'},
                    'transactionCount': {'$sum': 1}
                }
            },
            {'$sort': {'totalAmount': -1}},
            {
                '$project': {
                    '_id': 0,
                    'category': '$_id',
                    'totalAmount': 1,
                    'transactionCount': 1
                }
            }
        ]
        
        try:
            results = list(collection.aggregate(pipeline))
            return results
        except Exception as e:
            logger.error(f"Error fetching category spend: {str(e)}")
            raise

