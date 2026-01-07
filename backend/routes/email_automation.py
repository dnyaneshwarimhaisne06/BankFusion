from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
import os
import logging
from utils.auth_helpers import get_user_id_from_request
from db.mongo import MongoDB
from db.email_schema import EMAIL_CONSENT_COLLECTION, create_email_consent_doc
from services.email_listener import EmailListenerService
from utils.serializers import create_response

email_bp = Blueprint('email_automation', __name__)
logger = logging.getLogger(__name__)

@email_bp.route('/consent', methods=['POST'])
def save_consent():
    """Save or update user email consent"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    email_addr = data.get('email')
    
    if not email_addr:
        return jsonify({'error': 'Email is required'}), 400
        
    db = MongoDB.get_db()
    
    # Create document
    consent_doc = create_email_consent_doc(email_addr, user_id)
    
    # Update or Insert
    db[EMAIL_CONSENT_COLLECTION].update_one(
        {'userId': user_id},
        {'$set': consent_doc},
        upsert=True
    )
    
    return jsonify({'success': True, 'message': 'Consent saved successfully'})

@email_bp.route('/status', methods=['GET'])
def get_status():
    """Get current consent status"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    db = MongoDB.get_db()
    consent = db[EMAIL_CONSENT_COLLECTION].find_one({'userId': user_id})
    
    if consent:
        consent['_id'] = str(consent['_id'])
        return jsonify(consent)
    else:
        return jsonify({'isActive': False})

@email_bp.route('/consent', methods=['DELETE'])
def revoke_consent():
    """Revoke consent"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    db = MongoDB.get_db()
    db[EMAIL_CONSENT_COLLECTION].update_one(
        {'userId': user_id},
        {'$set': {'isActive': False, 'consentGiven': False}}
    )
    
    return jsonify({'success': True, 'message': 'Consent revoked'})

@email_bp.route('/simulate', methods=['POST'])
def simulate_email():
    """Simulate an incoming email (Dev/Test only)"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    email_addr = request.form.get('email')
    
    if not email_addr:
        return jsonify({'error': 'Email is required'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
        
    # Save file temporarily
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(filepath)
    
    try:
        result = EmailListenerService.simulate_email_arrival(email_addr, filepath)
        return jsonify(result)
    finally:
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@email_bp.route('/trigger', methods=['POST'])
def trigger_check():
    """Manually trigger email check"""
    try:
        logger.info("Manual email check triggered via API")
        stats = EmailListenerService.process_inbox()
        return jsonify({
            'success': True, 
            'message': 'Email check triggered',
            'details': stats
        })
    except Exception as e:
        logger.error(f"Manual trigger error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

