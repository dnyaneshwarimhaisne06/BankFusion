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
    def get_all(bank_type: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
        """Get all statements, optionally filtered by bank type and user_id"""
        db = MongoDB.get_db()
        collection = db[STATEMENTS_COLLECTION]
        
        query = {}
        if user_id:
            query['userId'] = user_id
        if bank_type:
            query['bankType'] = bank_type.upper()
        
        try:
            statements = list(collection.find(query).sort('createdAt', -1))
            return statements
        except Exception as e:
            logger.error(f"Error fetching statements: {str(e)}")
            raise
    
    @staticmethod
    def get_by_id(statement_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Get statement by ID, optionally filtered by user_id"""
        try:
            obj_id = ObjectId(statement_id)
        except InvalidId:
            raise ValueError(f"Invalid statement ID: {statement_id}")
        
        db = MongoDB.get_db()
        collection = db[STATEMENTS_COLLECTION]
        
        try:
            query = {'_id': obj_id}
            if user_id:
                query['userId'] = user_id
            statement = collection.find_one(query)
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
    
    @staticmethod
    def delete(statement_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a statement and all its associated transactions, optionally filtered by user_id"""
        try:
            obj_id = ObjectId(statement_id)
        except InvalidId:
            raise ValueError(f"Invalid statement ID: {statement_id}")
        
        db = MongoDB.get_db()
        statements_col = db[STATEMENTS_COLLECTION]
        transactions_col = db[TRANSACTIONS_COLLECTION]
        
        try:
            # First, check if statement exists and belongs to user
            query = {'_id': obj_id}
            if user_id:
                query['userId'] = user_id
            statement = statements_col.find_one(query)
            if not statement:
                return False
            
            # Delete all associated transactions (scoped to user_id if provided)
            transaction_query = {'statementId': obj_id}
            if user_id:
                transaction_query['userId'] = user_id
            delete_result = transactions_col.delete_many(transaction_query)
            logger.info(f"Deleted {delete_result.deleted_count} transactions for statement {statement_id}")
            
            # Delete the statement
            result = statements_col.delete_one(query)
            
            if result.deleted_count > 0:
                logger.info(f"Successfully deleted statement {statement_id}")
                return True
            else:
                logger.warning(f"Statement {statement_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting statement {statement_id}: {str(e)}")
            raise

class TransactionRepository:
    """Repository for bank_transactions collection"""
    
    @staticmethod
    def get_by_statement_id(statement_id: str, limit: int = 1000, user_id: Optional[str] = None) -> List[Dict]:
        """Get transactions for a specific statement, optionally filtered by user_id"""
        try:
            obj_id = ObjectId(statement_id)
        except InvalidId:
            raise ValueError(f"Invalid statement ID: {statement_id}")
        
        db = MongoDB.get_db()
        collection = db[TRANSACTIONS_COLLECTION]
        
        try:
            query = {'statementId': obj_id}
            if user_id:
                query['userId'] = user_id
            transactions = list(
                collection.find(query)
                .sort('date', 1)
                .limit(limit)
            )
            return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions for statement {statement_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_by_bank_type(bank_type: str, limit: int = 1000, user_id: Optional[str] = None) -> List[Dict]:
        """Get transactions by bank type, optionally filtered by user_id"""
        db = MongoDB.get_db()
        collection = db[TRANSACTIONS_COLLECTION]
        
        try:
            query = {'bankType': bank_type.upper()}
            if user_id:
                query['userId'] = user_id
            transactions = list(
                collection.find(query)
                .sort('date', -1)
                .limit(limit)
            )
            return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions for bank {bank_type}: {str(e)}")
            raise
    
    @staticmethod
    def get_category_spend(bank_type: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
        """Get category-wise spend (debit transactions only), optionally filtered by user_id"""
        db = MongoDB.get_db()
        collection = db[TRANSACTIONS_COLLECTION]
        
        # Match stage: only debit transactions
        match_stage = {'direction': 'debit'}
        if bank_type:
            match_stage['bankType'] = bank_type.upper()
        if user_id:
            match_stage['userId'] = user_id
        
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

