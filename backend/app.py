"""
BankFusion Flask REST API
Main Application Entry Point

IMPORTANT: Ensure virtual environment is activated before running!
Windows:  .venv\Scripts\activate
Linux/Mac: source .venv/bin/activate
"""

import sys
import os

# Check if running in virtual environment (recommended)
def check_venv():
    """Warn if not running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("=" * 70)
        print("WARNING: Virtual environment may not be activated!")
        print("=" * 70)
        print("For best results, activate the virtual environment:")
        print("  Windows:  .venv\\Scripts\\activate")
        print("  Linux/Mac: source .venv/bin/activate")
        print("=" * 70)
        print()

# Run venv check (non-blocking, just a warning)
check_venv()

from flask import Flask, jsonify
from flask_cors import CORS
from config import DEBUG, HOST, PORT
from db.mongo import MongoDB
from routes.statements import statements_bp
from routes.transactions import transactions_bp
from routes.analytics import analytics_bp
from routes.upload import upload_bp
from utils.serializers import create_response
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Register blueprints
app.register_blueprint(statements_bp, url_prefix='/api')
app.register_blueprint(transactions_bp, url_prefix='/api')
app.register_blueprint(analytics_bp, url_prefix='/api')
app.register_blueprint(upload_bp, url_prefix='/api')

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify(create_response(
        success=True,
        message="BankFusion API is running",
        data={
            'version': '1.0.0',
            'endpoints': {
                'upload': '/api/upload',
                'statements': '/api/statements',
                'transactions': '/api/transactions',
                'analytics': {
                    'category-spend': '/api/analytics/category-spend',
                    'bank-wise-spend': '/api/analytics/bank-wise-spend',
                    'summary': '/api/analytics/summary'
                }
            }
        }
    )), 200

@app.route('/api/health', methods=['GET'])
def health():
    """Detailed health check with MongoDB connection status"""
    try:
        # Test MongoDB connection
        db = MongoDB.get_db()
        db.command('ping')
        
        return jsonify(create_response(
            success=True,
            message="API and MongoDB are healthy",
            data={
                'api': 'healthy',
                'mongodb': 'connected'
            }
        )), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify(create_response(
            success=False,
            message="API is running but MongoDB connection failed",
            error=str(e)
        )), 503

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify(create_response(
        success=False,
        error="Endpoint not found"
    )), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify(create_response(
        success=False,
        error="Internal server error"
    )), 500

@app.before_request
def initialize_db():
    """Initialize MongoDB connection before each request"""
    try:
        MongoDB.get_db()
    except Exception as e:
        # Log error but don't crash - some endpoints might work without DB
        logger.warning(f"Failed to get MongoDB connection: {str(e)}")

if __name__ == '__main__':
    try:
        # Try to initialize MongoDB connection (non-blocking)
        try:
            MongoDB.connect()
            logger.info("MongoDB connection established")
        except Exception as db_error:
            logger.warning(f"MongoDB connection failed: {str(db_error)}")
            logger.warning("API will start but database operations may fail")
            logger.warning("Ensure MongoDB is running on: mongodb://localhost:27017")
        
        # Run Flask app
        logger.info(f"Starting Flask server on {HOST}:{PORT}")
        logger.info("API endpoints available at: http://localhost:5000")
        app.run(debug=DEBUG, host=HOST, port=PORT)
    except KeyboardInterrupt:
        logger.info("Shutting down Flask server...")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        MongoDB.close()
        logger.info("Application stopped")

