from datetime import datetime
from typing import Dict, Any

EMAIL_CONSENT_COLLECTION = 'email_consents'

def create_email_consent_doc(email: str, user_id: str, allowed_senders: list = None) -> Dict[str, Any]:
    """Create a new email consent document"""
    if allowed_senders is None:
        allowed_senders = []
        
    return {
        'userId': user_id,
        'email': email,
        'consentGiven': True,
        'consentTimestamp': datetime.now().isoformat(),
        'allowedSenders': allowed_senders,
        'isActive': True,
        'lastChecked': None,
        'processingHistory': [],
        'gmailOauth': {
            'provider': 'gmail',
            'configured': False
        }
    }
