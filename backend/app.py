"""
BankFusion Flask REST API
Main Application Entry Point
"""

import os
import logging
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from config import DEBUG, HOST, PORT
from db.mongo import MongoDB
from routes.statements import statements_bp
from routes.transactions import transactions_bp
from routes.analytics import analytics_bp
from routes.upload import upload_bp
from routes.account import account_bp
from routes.email_automation import email_bp
from utils.serializers import create_response

# ---------------------------------------------------
# Logging
# ---------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bankfusion")

# ---------------------------------------------------
# App
# ---------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------
# ✅ CORS CONFIG - Handles file uploads and all API routes
# ---------------------------------------------------
CORS(
    app,
    resources={r"/api/*": {
        "origins": "https://bankfusion-frontend-91cx.onrender.com",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "max_age": 3600
    }},
    supports_credentials=True
)

# ---------------------------------------------------
# Routes
# ---------------------------------------------------
app.register_blueprint(statements_bp, url_prefix="/api")
app.register_blueprint(transactions_bp, url_prefix="/api")
app.register_blueprint(analytics_bp, url_prefix="/api")
app.register_blueprint(upload_bp, url_prefix="/api")
app.register_blueprint(account_bp, url_prefix="/api")
app.register_blueprint(email_bp, url_prefix="/api/email-automation")

# ---------------------------------------------------
# Health
# ---------------------------------------------------
@app.route("/")
def root():
    return jsonify(create_response(
        success=True,
        message="BankFusion API is running"
    ))

@app.route("/api/health")
def health():
    try:
        db = MongoDB.get_db()
        db.command("ping")
        return jsonify(create_response(
            success=True,
            message="API & MongoDB healthy"
        ))
    except Exception as e:
        return jsonify(create_response(
            success=False,
            error=str(e)
        )), 500

# ---------------------------------------------------
# CORS Preflight Handler (for file uploads)
# ---------------------------------------------------
@app.before_request
def handle_cors_preflight():
    """Explicitly handle OPTIONS preflight requests"""
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin')
        if origin == 'https://bankfusion-frontend-91cx.onrender.com':
            response = Response(status=200)
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response

# ---------------------------------------------------
# Errors
# ---------------------------------------------------
@app.errorhandler(404)
def not_found(_):
    return jsonify(create_response(success=False, error="Not found")), 404

@app.errorhandler(500)
def server_error(error):
    import traceback
    error_trace = traceback.format_exc()
    logger.error(f"500 Error: {str(error)}")
    logger.error(f"Traceback: {error_trace}")
    return jsonify(create_response(success=False, error=f"Server error: {str(error)}")), 500

# ---------------------------------------------------
# Startup
# ---------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting BankFusion backend")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing")

    MongoDB.connect()
    logger.info("MongoDB connected")

    app.run(host=HOST, port=PORT, debug=DEBUG)
