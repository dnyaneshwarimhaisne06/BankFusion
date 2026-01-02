"""
Analytics API Routes
"""

from flask import Blueprint, request, jsonify
from services.analytics import AnalyticsService
from utils.serializers import create_response
from config import BANK_TYPES
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/category-spend', methods=['GET'])
def get_category_spend():
    """Get category-wise spend analysis"""
    try:
        # Get query parameters
        bank_type = request.args.get('bankType', None)
        
        # Validate bank type if provided
        if bank_type and bank_type.upper() not in BANK_TYPES:
            return jsonify(create_response(
                success=False,
                error=f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}"
            )), 400
        
        # Get analytics data
        results = AnalyticsService.get_category_spend(bank_type)
        
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
    """Get bank-wise expense summary"""
    try:
        # Get analytics data
        results = AnalyticsService.get_bank_wise_spend()
        
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
    """Get total debit vs credit summary"""
    try:
        # Get query parameters
        bank_type = request.args.get('bankType', None)
        
        # Validate bank type if provided
        if bank_type and bank_type.upper() not in BANK_TYPES:
            return jsonify(create_response(
                success=False,
                error=f"Invalid bank type. Supported types: {', '.join(BANK_TYPES)}"
            )), 400
        
        # Get analytics data
        results = AnalyticsService.get_total_summary(bank_type)
        
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

