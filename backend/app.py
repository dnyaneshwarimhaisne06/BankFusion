"""
BankFusion Flask REST API
Main Application Entry Point
"""

import sys
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
from utils.serializers import create_response

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# App
# --------------------------------------------------
app = Flask(__name__)

FRONTEND_ORIGIN = "https://bankfusion-frontend-91cx.onrender.com"

# --------------------------------------------------
# CORS (GLOBAL, SAFE, PRODUCTION)
# --------------------------------------------------
CORS(
    app,
    origins=[FRONTEND_ORIGIN],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    max_age=3600
)

# --------------------------------------------------
# Explicit OPTIONS Preflight Handler (CRITICAL)
# --------------------------------------------------
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = Response(status=200)
        response.headers["Access-Control-Allow-Origin"] = FRONTEND_ORIGIN
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

# --------------------------------------------------
# DB Init (runs AFTER preflight)
# --------------------------------------------------
@app.before_request
def initialize_db():
    try:
        MongoDB.get_db()
    except Exception as e:
        logger.warning(f"MongoDB init warning: {e}")

# --------------------------------------------------
# Blueprints
# --------------------------------------------------
app.register_blueprint(statements_bp, url_prefix="/api")
app.register_blueprint(transactions_bp, url_prefix="/api")
app.register_blueprint(analytics_bp, url_prefix="/api")
app.register_blueprint(upload_bp, url_prefix="/api")
app.register_blueprint(account_bp, url_prefix="/api")

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route("/")
def root():
    return jsonify(create_response(
        success=True,
        message="BankFusion API is running",
        data={
            "version": "1.0.0",
            "endpoints": [
                "/api/upload",
                "/api/statements",
                "/api/transactions",
                "/api/analytics/*"
            ]
        }
    )), 200

@app.route("/api/health", methods=["GET"])
def health():
    try:
        db = MongoDB.get_db()
        db.command("ping")
        return jsonify(create_response(
            success=True,
            message="API and MongoDB healthy"
        )), 200
    except Exception as e:
        return jsonify(create_response(
            success=False,
            error=str(e)
        )), 503

# --------------------------------------------------
# Errors
# --------------------------------------------------
@app.errorhandler(404)
def not_found(_):
    return jsonify(create_response(success=False, error="Not Found")), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(e)
    return jsonify(create_response(success=False, error="Internal Server Error")), 500

# --------------------------------------------------
# Startup
# --------------------------------------------------
if __name__ == "__main__":
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is missing")

        MongoDB.connect()
        logger.info("MongoDB connected")

        logger.info(f"Starting Flask on {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=DEBUG)

    except Exception as e:
        logger.error(e)
    finally:
        MongoDB.close()
