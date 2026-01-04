"""
Bank Transactions API Routes
"""

from flask import Blueprint, request, jsonify
from db.repositories import TransactionRepository, StatementRepository
from utils.serializers import serialize_documents, create_response
from config import BANK_TYPES
import logging

logger = logging.getLogger(__name__)

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Get transactions with optional filters (statementId or bankType)"""
    try:
        statement_id = request.args.get('statementId', None)
        bank_type = request.args.get('bankType', None)
        limit = request.args.get('limit', 1000, type=int)
        
        # Validate parameters
        if not statement_id and not bank_type:
            return jsonify(create_response(
                success=False,
                error="Please provide either statementId or bankType parameter"
            )), 400
        
        if statement_id and bank_type:
            return jsonify(create_response(
                success=False,
                error="Please provide either statementId or bankType, not both"
            )), 400
        
        if bank_type and bank_type.upper() not in BANK_TYPES:
            return jsonify(create_response(
                success=False,
                error=f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}"
            )), 400
        
        # Fetch transactions (scoped to user_id)
        if statement_id:
            # Verify statement exists and belongs to user
            statement = StatementRepository.get_by_id(statement_id, user_id=user_id)
            if not statement:
                return jsonify(create_response(
                    success=False,
                    error=f"Statement not found: {statement_id}"
                )), 404
            
            transactions = TransactionRepository.get_by_statement_id(statement_id, limit, user_id=user_id)
            message = f"Found {len(transactions)} transaction(s) for statement {statement_id}"
        else:
            transactions = TransactionRepository.get_by_bank_type(bank_type, limit, user_id=user_id)
            message = f"Found {len(transactions)} transaction(s) for bank {bank_type}"
        
        # Serialize documents
        serialized = serialize_documents(transactions)
        
        return jsonify(create_response(
            success=True,
            data=serialized,
            message=message
        )), 200
        
    except ValueError as e:
        return jsonify(create_response(
            success=False,
            error=str(e)
        )), 400
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

