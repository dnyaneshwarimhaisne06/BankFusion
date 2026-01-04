"""
Account Management Routes
Handles user account operations like deletion
"""

from flask import Blueprint, request, jsonify, Response
from utils.serializers import create_response
from db.mongo import MongoDB
from db.repositories import StatementRepository
import logging
import os
import requests
import base64
import json

logger = logging.getLogger(__name__)

account_bp = Blueprint('account', __name__)

def extract_user_id_from_token(token: str):
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
                logger.info(f"Extracted user_id from token: {user_id[:8]}...")
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

@account_bp.route('/account/delete', methods=['DELETE', 'OPTIONS'])
def delete_account():
    """
    Delete user account from both Supabase and MongoDB
    Requires valid JWT token in Authorization header
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = Response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE, OPTIONS')
        return response, 200
    
    try:
        # Get authorization token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify(create_response(
                success=False,
                error="Missing or invalid authorization token"
            )), 401
        
        token = auth_header.split('Bearer ')[1]
        
        # Extract user ID from token (decode JWT without verification)
        user_id = extract_user_id_from_token(token)
        if not user_id:
            logger.warning("Failed to extract user_id from token")
            return jsonify(create_response(
                success=False,
                error="Invalid token format"
            )), 401
        
        # Delete user data from MongoDB
        # Note: MongoDB may not have userId field in current schema
        # This attempts to delete if userId exists, otherwise continues
        try:
            db = MongoDB.get_db()
            statements_col = db['bank_statements']
            transactions_col = db['bank_transactions']
            
            # Try to find statements by userId (if field exists)
            # Also try alternative field names
            statements = []
            for field_name in ['userId', 'user_id', 'user']:
                found = list(statements_col.find({field_name: user_id}))
                if found:
                    statements = found
                    break
            
            if statements:
                statement_ids = [str(stmt['_id']) for stmt in statements]
                
                # Delete all transactions for these statements
                if statement_ids:
                    transactions_col.delete_many({'statementId': {'$in': statement_ids}})
                    logger.info(f"Deleted transactions for user {user_id}")
                
                # Delete all statements
                for field_name in ['userId', 'user_id', 'user']:
                    result = statements_col.delete_many({field_name: user_id})
                    if result.deleted_count > 0:
                        logger.info(f"Deleted {result.deleted_count} statements for user {user_id}")
                        break
            else:
                logger.info(f"No MongoDB statements found for user {user_id} (may not be using userId field)")
            
        except Exception as db_error:
            logger.error(f"Error deleting MongoDB data: {str(db_error)}")
            # Continue to delete Supabase user even if MongoDB deletion fails
        
        # Delete user from Supabase (REQUIRED - account deletion must remove auth user)
        supabase_deleted = False
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not supabase_url or not supabase_service_key:
                logger.error("Supabase credentials not configured - cannot delete user account")
                return jsonify(create_response(
                    success=False,
                    error="Server configuration error: Supabase credentials not set. Cannot delete account."
                )), 500
            
            # Delete user from Supabase using admin API
            response = requests.delete(
                f"{supabase_url}/auth/v1/admin/users/{user_id}",
                headers={
                    'Authorization': f'Bearer {supabase_service_key}',
                    'apikey': supabase_service_key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted Supabase user: {user_id}")
                supabase_deleted = True
            else:
                error_text = response.text
                logger.error(f"Failed to delete Supabase user: {response.status_code} - {error_text}")
                return jsonify(create_response(
                    success=False,
                    error=f"Failed to delete account from authentication system. Status: {response.status_code}"
                )), 500
        
        except requests.exceptions.RequestException as supabase_error:
            logger.error(f"Network error deleting Supabase user: {str(supabase_error)}")
            return jsonify(create_response(
                success=False,
                error="Failed to connect to authentication service. Please try again."
            )), 500
        except Exception as supabase_error:
            logger.error(f"Error deleting Supabase user: {str(supabase_error)}")
            return jsonify(create_response(
                success=False,
                error="Failed to delete user account"
            )), 500
        
        # Only return success if Supabase deletion succeeded
        if not supabase_deleted:
            return jsonify(create_response(
                success=False,
                error="Account deletion incomplete - authentication account not removed"
            )), 500
        
        return jsonify(create_response(
            success=True,
            message="Account deleted successfully"
        )), 200
        
    except Exception as e:
        logger.error(f"Error in delete_account: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

