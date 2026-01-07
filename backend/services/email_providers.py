
import os
import logging
import requests
import json
import base64
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class EmailProvider(ABC):
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body: str, attachment_path: str = None) -> bool:
        """Send an email. Returns True if successful, False otherwise."""
        pass

class Msg91EmailProvider(EmailProvider):
    def __init__(self):
        self.api_key = os.getenv('MSG91_API_KEY')
        self.sender_email = os.getenv('MSG91_SENDER_EMAIL')
        self.endpoint = os.getenv('MSG91_EMAIL_ENDPOINT', 'https://api.msg91.com/api/v5/email/send')

    def send_email(self, to_email, subject, body, attachment_path=None):
        if not self.api_key or not self.sender_email:
            logger.warning("MSG91 provider not configured (missing API key or sender email).")
            return False

        payload = {
            "to": [{"email": to_email}],
            "from": {"email": self.sender_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }

        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                payload["attachments"] = [{
                    "name": os.path.basename(attachment_path),
                    "content": b64
                }]
            except Exception as e:
                logger.error(f"Attachment encoding failed: {str(e)}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, data=json.dumps(payload), timeout=10)
            if 200 <= resp.status_code < 300:
                logger.info(f"MSG91: Email sent to {to_email}")
                return True
            else:
                logger.error(f"MSG91 send failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"MSG91 request error: {str(e)}")
            return False

class SendGridEmailProvider(EmailProvider):
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL')
        self.endpoint = "https://api.sendgrid.com/v3/mail/send"

    def send_email(self, to_email, subject, body, attachment_path=None):
        if not self.api_key or not self.from_email:
            logger.warning("SendGrid provider not configured (missing API key or from email).")
            return False

        payload = {
            "personalizations": [{
                "to": [{"email": to_email}]
            }],
            "from": {"email": self.from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }

        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                payload["attachments"] = [{
                    "content": b64,
                    "filename": os.path.basename(attachment_path),
                    "type": "application/pdf",  # Assuming PDF based on context
                    "disposition": "attachment"
                }]
            except Exception as e:
                logger.error(f"Attachment encoding failed: {str(e)}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, data=json.dumps(payload), timeout=10)
            if 200 <= resp.status_code < 300:
                logger.info(f"SendGrid: Email sent to {to_email}")
                return True
            else:
                logger.error(f"SendGrid send failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"SendGrid request error: {str(e)}")
            return False

def get_email_provider() -> EmailProvider:
    """Factory to get the configured email provider"""
    provider_name = os.getenv('EMAIL_PROVIDER', 'sendgrid').lower()
    
    if provider_name == 'msg91':
        return Msg91EmailProvider()
    elif provider_name == 'sendgrid':
        return SendGridEmailProvider()
    else:
        logger.warning(f"Unknown email provider '{provider_name}'. Defaulting to SendGrid.")
        return SendGridEmailProvider()
