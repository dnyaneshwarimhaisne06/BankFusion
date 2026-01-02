"""
JSON Serializers for MongoDB Documents
"""

from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List
import json

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB documents"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def serialize_document(doc: Dict) -> Dict:
    """Serialize a single MongoDB document"""
    if doc is None:
        return None
    
    # Convert ObjectId to string
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    
    # Convert statementId to string if present
    if 'statementId' in doc and isinstance(doc['statementId'], ObjectId):
        doc['statementId'] = str(doc['statementId'])
    
    # Convert datetime to ISO format
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            doc[key] = str(value)
    
    return doc

def serialize_documents(docs: List[Dict]) -> List[Dict]:
    """Serialize a list of MongoDB documents"""
    return [serialize_document(doc) for doc in docs]

def create_response(success: bool, data: Any = None, message: str = None, error: str = None) -> Dict:
    """Create standardized API response"""
    response = {
        'success': success
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    if error:
        response['error'] = error
    
    return response

