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
from db.gmail_tokens import upsert_gmail_token

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

@email_bp.route('/gmail/auth-url', methods=['GET'])
def gmail_auth_url():
    """Return Google OAuth URL forcing account selection and offline access"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    client_id = os.getenv('GMAIL_CLIENT_ID')
    redirect_uri = os.getenv('GMAIL_REDIRECT_URI')
    if not client_id or not redirect_uri:
        return jsonify({'error': 'Gmail OAuth not configured'}), 500
    scope = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
        'state': user_id
    }
    from urllib.parse import urlencode
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return jsonify({'auth_url': url})

@email_bp.route('/gmail/start', methods=['GET'])
def gmail_start():
    """Redirect user to Google OAuth with forced consent and offline access"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    client_id = os.getenv('GMAIL_CLIENT_ID')
    redirect_uri = os.getenv('GMAIL_REDIRECT_URI')
    if not client_id or not redirect_uri:
        return jsonify({'error': 'Gmail OAuth not configured'}), 500
    scope = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
        'state': user_id
    }
    from urllib.parse import urlencode
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    from flask import redirect
    return redirect(url)

@email_bp.route('/gmail/callback', methods=['GET'])
def gmail_callback():
    """Exchange authorization code for tokens and store per-user"""
    code = request.args.get('code')
    user_id = request.args.get('state')
    if not code or not user_id:
        return jsonify({'error': 'Missing code/state'}), 400
    client_id = os.getenv('GMAIL_CLIENT_ID')
    client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    redirect_uri = os.getenv('GMAIL_REDIRECT_URI')
    if not client_id or not client_secret or not redirect_uri:
        return jsonify({'error': 'Gmail OAuth not configured'}), 500
    # Token exchange
    import requests
    token_resp = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        },
        timeout=10
    )
    if token_resp.status_code != 200:
        return jsonify({'error': 'Token exchange failed', 'details': token_resp.text}), 500
    token_json = token_resp.json()
    access_token = token_json.get('access_token')
    refresh_token = token_json.get('refresh_token')
    expires_in = token_json.get('expires_in', 0)
    if not access_token or not refresh_token:
        return jsonify({'error': 'Missing tokens in response'}), 500
    # Determine email via Gmail API with the fresh token
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret
        )
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
        email_addr = profile.get('emailAddress')
    except Exception:
        email_addr = None
    upsert_gmail_token(user_id, email_addr or '', access_token, refresh_token, expires_in)
    logger.info(f"Gmail OAuth saved for user {user_id} email {email_addr}")
    return jsonify({'success': True, 'email': email_addr})

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

