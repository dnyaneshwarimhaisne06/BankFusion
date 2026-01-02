"""
Bank Statements API Routes
"""

from flask import Blueprint, request, jsonify
from db.repositories import StatementRepository
from utils.serializers import serialize_document, serialize_documents, create_response
from config import BANK_TYPES
import logging

logger = logging.getLogger(__name__)

statements_bp = Blueprint('statements', __name__)

@statements_bp.route('/statements', methods=['GET'])
def get_statements():
    """Get all bank statements with optional bank type filter"""
    try:
        # Get query parameters
        bank_type = request.args.get('bankType', None)
        
        # Validate bank type if provided
        if bank_type and bank_type.upper() not in BANK_TYPES:
            return jsonify(create_response(
                success=False,
                error=f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}"
            )), 400
        
        # Fetch statements
        statements = StatementRepository.get_all(bank_type)
        
        # Serialize documents
        serialized = serialize_documents(statements)
        
        return jsonify(create_response(
            success=True,
            data=serialized,
            message=f"Found {len(serialized)} statement(s)"
        )), 200
        
    except Exception as e:
        logger.error(f"Error in get_statements: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

@statements_bp.route('/statements/<statement_id>', methods=['GET'])
def get_statement(statement_id: str):
    """Get a single statement by ID"""
    try:
        # Fetch statement
        statement = StatementRepository.get_by_id(statement_id)
        
        if not statement:
            return jsonify(create_response(
                success=False,
                error=f"Statement not found: {statement_id}"
            )), 404
        
        # Serialize document
        serialized = serialize_document(statement)
        
        return jsonify(create_response(
            success=True,
            data=serialized
        )), 200
        
    except ValueError as e:
        return jsonify(create_response(
            success=False,
            error=str(e)
        )), 400
    except Exception as e:
        logger.error(f"Error in get_statement: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

