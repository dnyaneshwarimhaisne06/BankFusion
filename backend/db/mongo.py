"""
MongoDB Connection Manager
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import MONGO_URI, DB_NAME
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection singleton"""
    _client = None
    _db = None
    
    @classmethod
    def connect(cls):
        """Establish MongoDB connection"""
        if cls._client is None:
            try:
                cls._client = MongoClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                cls._client.server_info()
                cls._db = cls._client[DB_NAME]
                logger.info(f"Connected to MongoDB: {MONGO_URI}")
                return cls._db
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"MongoDB connection failed: {str(e)}")
                raise
        return cls._db
    
    @classmethod
    def get_db(cls):
        """Get database instance"""
        if cls._db is None:
            return cls.connect()
        return cls._db
    
    @classmethod
    def close(cls):
        """Close MongoDB connection"""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            logger.info("MongoDB connection closed")

