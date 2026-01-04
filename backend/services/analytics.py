"""
Analytics Service - Business Logic for Analytics Queries
"""

from typing import List, Dict, Optional
from db.repositories import TransactionRepository
from config import BANK_TYPES
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analytics operations"""
    
    @staticmethod
    def get_category_spend(bank_type: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get category-wise spend analysis, optionally scoped to user_id
        
        Rules:
        - Only debit transactions count as expenses
        - Credit transactions are excluded
        - Results sorted by total amount (descending)
        """
        try:
            # Validate bank type if provided
            if bank_type and bank_type.upper() not in BANK_TYPES:
                raise ValueError(f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}")
            
            # Get category spend from repository (scoped to user_id)
            results = TransactionRepository.get_category_spend(bank_type, user_id=user_id)
            
            # Format results
            formatted_results = []
            for item in results:
                formatted_results.append({
                    'category': item.get('category', 'unknown'),
                    'totalAmount': round(item.get('totalAmount', 0), 2),
                    'transactionCount': item.get('transactionCount', 0)
                })
            
            return formatted_results
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in get_category_spend: {str(e)}")
            raise Exception("Failed to fetch category spend analytics")
    
    @staticmethod
    def get_bank_wise_spend(user_id: Optional[str] = None) -> List[Dict]:
        """
        Get bank-wise expense summary, optionally scoped to user_id
        
        Returns total debit (expenses) and credit (income) per bank
        """
        try:
            from db.mongo import MongoDB
            from config import TRANSACTIONS_COLLECTION
            
            db = MongoDB.get_db()
            collection = db[TRANSACTIONS_COLLECTION]
            
            # Match stage with user_id filter if provided
            match_stage = {}
            if user_id:
                match_stage['userId'] = user_id
            
            pipeline = []
            if match_stage:
                pipeline.append({'$match': match_stage})
            
            pipeline.append({
                '$group': {
                    '_id': '$bankType',
                    'totalDebit': {
                        '$sum': {
                            '$cond': [{'$eq': ['$direction', 'debit']}, '$amount', 0]
                        }
                    },
                    'totalCredit': {
                        '$sum': {
                            '$cond': [{'$eq': ['$direction', 'credit']}, '$amount', 0]
                        }
                    },
                    'debitCount': {
                        '$sum': {
                            '$cond': [{'$eq': ['$direction', 'debit']}, 1, 0]
                        }
                    },
                    'creditCount': {
                        '$sum': {
                            '$cond': [{'$eq': ['$direction', 'credit']}, 1, 0]
                        }
                    }
                }
            })
            
            pipeline.append({
                '$project': {
                    '_id': 0,
                    'bankType': '$_id',
                    'totalDebit': {'$round': ['$totalDebit', 2]},
                    'totalCredit': {'$round': ['$totalCredit', 2]},
                    'debitCount': 1,
                    'creditCount': 1,
                    'netAmount': {'$round': [{'$subtract': ['$totalCredit', '$totalDebit']}, 2]}
                }
            })
            
            pipeline.append({'$sort': {'totalDebit': -1}})
            
            results = list(collection.aggregate(pipeline))
            return results
            
        except Exception as e:
            logger.error(f"Error in get_bank_wise_spend: {str(e)}")
            raise Exception("Failed to fetch bank-wise spend analytics")
    
    @staticmethod
    def get_total_summary(bank_type: Optional[str] = None, user_id: Optional[str] = None) -> Dict:
        """
        Get total debit vs credit summary, optionally scoped to user_id
        
        Returns overall financial summary
        """
        try:
            from db.mongo import MongoDB
            from config import TRANSACTIONS_COLLECTION
            
            db = MongoDB.get_db()
            collection = db[TRANSACTIONS_COLLECTION]
            
            match_stage = {}
            if bank_type:
                match_stage['bankType'] = bank_type.upper()
            if user_id:
                match_stage['userId'] = user_id
            
            pipeline = [
                {'$match': match_stage} if match_stage else {'$match': {}},
                {
                    '$group': {
                        '_id': None,
                        'totalDebit': {
                            '$sum': {
                                '$cond': [{'$eq': ['$direction', 'debit']}, '$amount', 0]
                            }
                        },
                        'totalCredit': {
                            '$sum': {
                                '$cond': [{'$eq': ['$direction', 'credit']}, '$amount', 0]
                            }
                        },
                        'debitCount': {
                            '$sum': {
                                '$cond': [{'$eq': ['$direction', 'debit']}, 1, 0]
                            }
                        },
                        'creditCount': {
                            '$sum': {
                                '$cond': [{'$eq': ['$direction', 'credit']}, 1, 0]
                            }
                        }
                    }
                },
                {
                    '$project': {
                        '_id': 0,
                        'totalDebit': {'$round': ['$totalDebit', 2]},
                        'totalCredit': {'$round': ['$totalCredit', 2]},
                        'debitCount': 1,
                        'creditCount': 1,
                        'netAmount': {'$round': [{'$subtract': ['$totalCredit', '$totalDebit']}, 2]},
                        'totalTransactions': {'$add': ['$debitCount', '$creditCount']}
                    }
                }
            ]
            
            results = list(collection.aggregate(pipeline))
            if results:
                return results[0]
            else:
                return {
                    'totalDebit': 0.0,
                    'totalCredit': 0.0,
                    'debitCount': 0,
                    'creditCount': 0,
                    'netAmount': 0.0,
                    'totalTransactions': 0
                }
            
        except Exception as e:
            logger.error(f"Error in get_total_summary: {str(e)}")
            raise Exception("Failed to fetch total summary analytics")

