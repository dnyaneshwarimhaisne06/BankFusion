"""
Authentication Helper Utilities
Extracts user_id from Supabase JWT tokens
"""

import base64
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from Supabase JWT token by decoding it
    Returns user_id if valid, None otherwise
    """
    try:
        # JWT tokens have 3 parts separated by dots: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            logger.warning("Invalid JWT token format")
            return None
        
        # Decode the payload (second part)
        # Add padding if needed for base64 decoding
        payload = parts[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        try:
            decoded = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded)
            
            # Supabase stores user_id in the 'sub' claim
            user_id = payload_data.get('sub')
            
            if user_id:
                logger.debug(f"Extracted user_id from token: {user_id[:8]}...")
                return user_id
            else:
                logger.warning("Token payload does not contain 'sub' claim")
                return None
                
        except (Exception, json.JSONDecodeError) as e:
            logger.error(f"Error decoding token payload: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting user_id from token: {str(e)}")
        return None

def extract_user_email_from_token(token: str) -> Optional[str]:
    """
    Extract user email from Supabase JWT token by decoding it
    Returns email if valid, None otherwise
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        payload = parts[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        return payload_data.get('email')
    except Exception as e:
        logger.error(f"Error extracting email from token: {str(e)}")
        return None

def get_user_id_from_request(request) -> Optional[str]:
    """
    Extract user_id from Authorization header in Flask request
    Returns user_id if valid token found, None otherwise
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split('Bearer ')[1]
        return extract_user_id_from_token(token)
    except Exception as e:
        logger.error(f"Error getting user_id from request: {str(e)}")
        return None

def get_user_email_from_request(request) -> Optional[str]:
    """
    Extract user email from Authorization header in Flask request
    Returns email if valid token found, None otherwise
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split('Bearer ')[1]
        return extract_user_email_from_token(token)
    except Exception as e:
        logger.error(f"Error getting user_email from request: {str(e)}")
        return None

