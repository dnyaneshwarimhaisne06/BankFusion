"""
Account Management Routes
Handles user account operations like deletion
"""

from flask import Blueprint, request, jsonify
from utils.serializers import create_response
from db.mongo import MongoDB
from db.repositories import StatementRepository
import logging
import os
import requests

logger = logging.getLogger(__name__)

account_bp = Blueprint('account', __name__)

def verify_supabase_token(token: str):
    """
    Verify Supabase JWT token and extract user ID
    Returns user_id if valid, None otherwise
    """
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            logger.warning("Supabase credentials not configured")
            return None
        
        # Verify token with Supabase
        response = requests.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                'Authorization': f'Bearer {token}',
                'apikey': supabase_service_key
            }
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('id')
        else:
            logger.warning(f"Token verification failed: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None

@account_bp.route('/account/delete', methods=['DELETE'])
def delete_account():
    """
    Delete user account from both Supabase and MongoDB
    Requires valid JWT token in Authorization header
    """
    try:
        # Get authorization token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify(create_response(
                success=False,
                error="Missing or invalid authorization token"
            )), 401
        
        token = auth_header.split('Bearer ')[1]
        
        # Verify token and get user ID
        user_id = verify_supabase_token(token)
        if not user_id:
            return jsonify(create_response(
                success=False,
                error="Invalid or expired token"
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
        
        # Delete user from Supabase
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if supabase_url and supabase_service_key:
                response = requests.delete(
                    f"{supabase_url}/auth/v1/admin/users/{user_id}",
                    headers={
                        'Authorization': f'Bearer {supabase_service_key}',
                        'apikey': supabase_service_key
                    }
                )
                
                if response.status_code not in [200, 204]:
                    logger.error(f"Failed to delete Supabase user: {response.status_code}")
                    return jsonify(create_response(
                        success=False,
                        error="Failed to delete user account"
                    )), 500
            else:
                logger.warning("Supabase credentials not configured - skipping Supabase user deletion")
        
        except Exception as supabase_error:
            logger.error(f"Error deleting Supabase user: {str(supabase_error)}")
            return jsonify(create_response(
                success=False,
                error="Failed to delete user account"
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

