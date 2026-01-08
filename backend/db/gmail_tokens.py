"""
MongoDB schema and helpers for per-user Gmail OAuth tokens
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from db.mongo import MongoDB

GMAIL_TOKENS_COLLECTION = 'gmail_tokens'

def upsert_gmail_token(user_id: str, email: str, access_token: str, refresh_token: str, expires_in: int) -> None:
    """Insert or update Gmail OAuth token for a user"""
    db = MongoDB.get_db()
    expiry = datetime.utcnow() + timedelta(seconds=int(expires_in or 0))
    doc = {
        'userId': user_id,
        'email': email,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expiry': expiry
    }
    db[GMAIL_TOKENS_COLLECTION].update_one({'userId': user_id}, {'$set': doc}, upsert=True)

def get_gmail_token(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Gmail OAuth token document by user ID"""
    db = MongoDB.get_db()
    return db[GMAIL_TOKENS_COLLECTION].find_one({'userId': user_id})

