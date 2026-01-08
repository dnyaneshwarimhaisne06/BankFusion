"""
MongoDB schema and helpers for per-user Gmail OAuth tokens
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from db.mongo import MongoDB

GMAIL_TOKENS_COLLECTION = 'gmail_tokens'

def upsert_gmail_token(user_id: str, gmail_email: str, access_token: str, refresh_token: str, expires_in: int) -> None:
    db = MongoDB.get_db()
    expiry = datetime.utcnow() + timedelta(seconds=int(expires_in or 0))
    doc = {
        'user_id': user_id,
        'gmail_email': gmail_email,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expiry': expiry,
        'created_at': datetime.utcnow()
    }
    db[GMAIL_TOKENS_COLLECTION].update_one({'user_id': user_id}, {'$set': doc}, upsert=True)

def get_gmail_token(user_id: str) -> Optional[Dict[str, Any]]:
    db = MongoDB.get_db()
    return db[GMAIL_TOKENS_COLLECTION].find_one({'user_id': user_id})
