"""
PDF Upload API Routes
"""

from flask import Blueprint, request, jsonify, Response
from werkzeug.utils import secure_filename
import os
import tempfile
from pathlib import Path
from services.pdf_processor import PDFProcessor
from services.email_listener import EmailListenerService
from utils.serializers import create_response
from utils.auth_helpers import get_user_id_from_request, get_user_email_from_request
from db.mongo import MongoDB
from db.email_schema import EMAIL_CONSENT_COLLECTION
import logging

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

# Upload configuration
# Use /tmp on Render (writable), or local uploads folder for development
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads'))
# On Render, use /tmp for writable storage
if not os.path.exists(UPLOAD_FOLDER) or not os.access(UPLOAD_FOLDER, os.W_OK):
    UPLOAD_FOLDER = '/tmp/bankfusion_uploads'

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure upload folder exists
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
except Exception as e:
    logger.error(f"Failed to create upload folder {UPLOAD_FOLDER}: {str(e)}")
    # Fallback to /tmp
    UPLOAD_FOLDER = '/tmp/bankfusion_uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info(f"Using fallback upload folder: {UPLOAD_FOLDER}")

@upload_bp.route('/upload', methods=['POST', 'OPTIONS'])
def upload_pdf():
    """Upload and process PDF bank statement"""
    # Handle CORS preflight (explicit handling for file uploads)
    if request.method == 'OPTIONS':
        response = Response(status=200)
        response.headers.add('Access-Control-Allow-Origin', 'https://bankfusion-frontend-91cx.onrender.com')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
    
    try:
        # Extract user_id from JWT token
        user_id = get_user_id_from_request(request)
        if not user_id:
            logger.warning("Upload attempted without authentication")
            return jsonify(create_response(
                success=False,
                error="Authentication required. Please log in."
            )), 401
        
        logger.info(f"Upload request from user: {user_id[:8]}...")
        
        # Check if file is present
        if 'pdf' not in request.files and 'file' not in request.files:
            logger.warning("Upload attempted without file")
            return jsonify(create_response(
                success=False,
                error="No file provided. Please upload a PDF file."
            )), 400
        
        # Get file (support both 'pdf' and 'file' field names)
        file = request.files.get('pdf') or request.files.get('file')
        logger.info(f"Received file: {file.filename if file else 'None'}")
        
        # Validate file
        is_valid, error_msg = PDFProcessor.validate_pdf_file(file)
        if not is_valid:
            return jsonify(create_response(
                success=False,
                error=error_msg
            )), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify(create_response(
                success=False,
                error=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )), 400
        
        # Save uploaded file
        pdf_path = PDFProcessor.save_uploaded_file(file, UPLOAD_FOLDER)
        
        try:
            # Verify MongoDB connection before processing
            try:
                db = MongoDB.get_db()
                db.command('ping')
                logger.info("MongoDB connection verified")
            except Exception as db_error:
                logger.error(f"MongoDB connection failed: {str(db_error)}")
                raise Exception(f"MongoDB connection failed: {str(db_error)}")
            
            # Process PDF: Extract → Normalize → Store in MongoDB (with user_id)
            logger.info(f"Starting PDF processing for user: {user_id[:8]}...")
            result = PDFProcessor.process_pdf_to_mongodb(pdf_path, user_id=user_id)
            logger.info(f"PDF processing completed. Transactions: {result.get('transactionsInserted', 0)}")
            
            # Clean up uploaded file after processing
            try:
                os.remove(pdf_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {str(e)}")
            
            return jsonify(create_response(
                success=True,
                data=result,
                message=f"PDF processed successfully. {result['transactionsInserted']} transactions stored."
            )), 200
            
        except ValueError as e:
            # Clean up on error
            try:
                os.remove(pdf_path)
            except:
                pass
            return jsonify(create_response(
                success=False,
                error=str(e)
            )), 400
        except Exception as e:
            # Clean up on error
            try:
                os.remove(pdf_path)
            except:
                pass
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error processing PDF: {str(e)}")
            logger.error(f"Traceback: {error_trace}")
            return jsonify(create_response(
                success=False,
                error=f"Failed to process PDF: {str(e)}"
            )), 500
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in upload_pdf: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        return jsonify(create_response(
            success=False,
            error=f"Internal server error: {str(e)}"
        )), 500

