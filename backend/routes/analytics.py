"""
Analytics API Routes
"""

from flask import Blueprint, request, jsonify
from services.analytics import AnalyticsService
from utils.serializers import create_response
from utils.auth_helpers import get_user_id_from_request
from config import BANK_TYPES
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/category-spend', methods=['GET'])
def get_category_spend():
    """Get category-wise spend analysis, scoped to authenticated user"""
    try:
        # Extract user_id from JWT token
        user_id = get_user_id_from_request(request)
        if not user_id:
            return jsonify(create_response(
                success=False,
                error="Authentication required. Please log in."
            )), 401
        
        # Get query parameters
        bank_type = request.args.get('bankType', None)
        
        # Validate bank type if provided
        if bank_type and bank_type.upper() not in BANK_TYPES:
            return jsonify(create_response(
                success=False,
                error=f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}"
            )), 400
        
        # Get analytics data (scoped to user_id)
        results = AnalyticsService.get_category_spend(bank_type, user_id=user_id)
        
        # Prepare response message
        if bank_type:
            message = f"Category spend analysis for {bank_type}"
        else:
            message = "Category spend analysis (all banks)"
        
        return jsonify(create_response(
            success=True,
            data=results,
            message=message
        )), 200
        
    except ValueError as e:
        return jsonify(create_response(
            success=False,
            error=str(e)
        )), 400
    except Exception as e:
        logger.error(f"Error in get_category_spend: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

@analytics_bp.route('/analytics/bank-wise-spend', methods=['GET'])
def get_bank_wise_spend():
    """Get bank-wise expense summary, scoped to authenticated user"""
    try:
        # Extract user_id from JWT token
        user_id = get_user_id_from_request(request)
        if not user_id:
            return jsonify(create_response(
                success=False,
                error="Authentication required. Please log in."
            )), 401
        
        # Get analytics data (scoped to user_id)
        results = AnalyticsService.get_bank_wise_spend(user_id=user_id)
        
        return jsonify(create_response(
            success=True,
            data=results,
            message="Bank-wise spend analysis"
        )), 200
        
    except Exception as e:
        logger.error(f"Error in get_bank_wise_spend: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

@analytics_bp.route('/analytics/summary', methods=['GET'])
def get_summary():
    """Get total debit vs credit summary, scoped to authenticated user"""
    try:
        # Extract user_id from JWT token
        user_id = get_user_id_from_request(request)
        if not user_id:
            return jsonify(create_response(
                success=False,
                error="Authentication required. Please log in."
            )), 401
        
        # Get query parameters
        bank_type = request.args.get('bankType', None)
        
        # Validate bank type if provided
        if bank_type and bank_type.upper() not in BANK_TYPES:
            return jsonify(create_response(
                success=False,
                error=f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}"
            )), 400
        
        # Get analytics data (scoped to user_id)
        results = AnalyticsService.get_total_summary(bank_type, user_id=user_id)
        
        # Prepare response message
        if bank_type:
            message = f"Financial summary for {bank_type}"
        else:
            message = "Financial summary (all banks)"
        
        return jsonify(create_response(
            success=True,
            data=results,
            message=message
        )), 200
        
    except ValueError as e:
        return jsonify(create_response(
            success=False,
            error=str(e)
        )), 400
    except Exception as e:
        logger.error(f"Error in get_summary: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

@analytics_bp.route('/analytics/ai-summary/<statement_id>', methods=['GET'])
def get_ai_summary(statement_id: str):
    """Generate AI-powered expense summary report for a statement, scoped to authenticated user"""
    try:
        # Extract user_id from JWT token
        user_id = get_user_id_from_request(request)
        if not user_id:
            return jsonify(create_response(
                success=False,
                error="Authentication required. Please log in."
            )), 401
        
        from db.repositories import StatementRepository, TransactionRepository
        from services.ai_summary import generate_expense_summary
        
        # Fetch statement (scoped to user_id)
        statement = StatementRepository.get_by_id(statement_id, user_id=user_id)
        if not statement:
            return jsonify(create_response(
                success=False,
                error=f"Statement not found: {statement_id}"
            )), 404
        
        # Fetch transactions (scoped to user_id)
        transactions = TransactionRepository.get_by_statement_id(statement_id, limit=1000, user_id=user_id)
        
        # Prepare statement data
        statement_data = {
            'bank_name': statement.get('bankType', 'Unknown'),
            'account_number': statement.get('accountNumber'),
            'account_holder': statement.get('accountHolder'),
            'file_name': statement.get('fileName', 'Untitled'),
        }
        
        # Convert transactions to format expected by AI summary
        transaction_list = []
        for txn in transactions:
            # Convert MongoDB format (amount + direction) to debit/credit
            debit = None
            credit = None
            
            if txn.get('amount') is not None and txn.get('direction'):
                amount = float(txn.get('amount', 0))
                direction = txn.get('direction', '').lower()
                if direction == 'debit':
                    debit = amount
                else:
                    credit = amount
            else:
                # Legacy format
                debit = txn.get('debit')
                credit = txn.get('credit')
            
            transaction_list.append({
                'date': str(txn.get('date', '')),
                'description': txn.get('description', ''),
                'debit': debit,
                'credit': credit,
                'balance': txn.get('balance'),
                'category': txn.get('category', 'Uncategorized'),
            })
        
        # Generate AI summary
        summary_result = generate_expense_summary(statement_data, transaction_list)
        
        if summary_result.get('success'):
            return jsonify(create_response(
                success=True,
                data=summary_result
            )), 200
        else:
            # Return fallback summary if AI fails
            return jsonify(create_response(
                success=True,
                data=summary_result,
                message="AI summary unavailable, using basic summary"
            )), 200
            
    except Exception as e:
        logger.error(f"Error generating AI summary: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

