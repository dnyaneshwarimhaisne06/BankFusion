"""
PDF Upload API Routes
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from pathlib import Path
from services.pdf_processor import PDFProcessor
from utils.serializers import create_response
from utils.auth_helpers import get_user_id_from_request
import logging

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@upload_bp.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload and process PDF bank statement"""
    try:
        # Extract user_id from JWT token
        user_id = get_user_id_from_request(request)
        if not user_id:
            return jsonify(create_response(
                success=False,
                error="Authentication required. Please log in."
            )), 401
        
        # Check if file is present
        if 'pdf' not in request.files and 'file' not in request.files:
            return jsonify(create_response(
                success=False,
                error="No file provided. Please upload a PDF file."
            )), 400
        
        # Get file (support both 'pdf' and 'file' field names)
        file = request.files.get('pdf') or request.files.get('file')
        
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
            # Process PDF: Extract → Normalize → Store in MongoDB (with user_id)
            result = PDFProcessor.process_pdf_to_mongodb(pdf_path, user_id=user_id)
            
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
            logger.error(f"Error processing PDF: {str(e)}")
            return jsonify(create_response(
                success=False,
                error="Failed to process PDF. Please check the file format."
            )), 500
            
    except Exception as e:
        logger.error(f"Error in upload_pdf: {str(e)}")
        return jsonify(create_response(
            success=False,
            error="Internal server error"
        )), 500

