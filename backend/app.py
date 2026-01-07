"""
BankFusion Flask REST API
Main Application Entry Point
"""

import os
import logging
import threading
import time
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
# Background Tasks
# ---------------------------------------------------
def start_background_poller():
    """Start the background email polling thread"""
    def _email_poll_loop():
        # Import inside to avoid potential circular imports during app initialization
        try:
            from services.email_listener import EmailListenerService
            interval = int(os.getenv("EMAIL_POLL_INTERVAL_SECONDS", "15"))
            logger.info(f"Starting email poll loop with interval {interval}s")
            
            # Initial delay to ensure app is fully loaded
            time.sleep(5)
            
            while True:
                try:
                    EmailListenerService.process_inbox()
                except Exception as e:
                    logger.error(f"Email polling error: {e}")
                time.sleep(interval)
        except Exception as e:
            logger.error(f"Failed to start poller loop: {e}")

    # Only start if enabled
    if os.getenv("EMAIL_POLL_ENABLED", "true").lower() == "true":
        # Prevent double execution in local dev reloader (Werkzeug)
        # WERKZEUG_RUN_MAIN is set in the reloader process.
        # If DEBUG is False (Production), we just run.
        # If DEBUG is True (Local), we only run if WERKZEUG_RUN_MAIN is true (the reloader) 
        # OR if we are not using reloader (which we can't easily check, but usually we are).
        # Actually, standard practice:
        if not DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            try:
                t = threading.Thread(target=_email_poll_loop, daemon=True)
                t.start()
                logger.info("Background email poller thread initialized")
            except Exception as e:
                logger.error(f"Failed to start background thread: {e}")

# Start the poller when app is loaded
start_background_poller()

# ---------------------------------------------------
# Startup
# ---------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting BankFusion backend")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing")

    # Explicit connect in main (optional now as get_db handles it)
    MongoDB.connect()
    logger.info("MongoDB connected")

    app.run(host=HOST, port=PORT, debug=DEBUG)
