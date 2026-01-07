import email
import os
import tempfile
import logging
import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
import requests
import smtplib
from email.message import EmailMessage

from db.mongo import MongoDB
from db.email_schema import EMAIL_CONSENT_COLLECTION
from services.pdf_processor import PDFProcessor
from services.ai_summary import generate_expense_summary
from services.report_generator import ReportGenerator
from config import STATEMENTS_COLLECTION, TRANSACTIONS_COLLECTION

logger = logging.getLogger(__name__)

# Constants
EMAIL_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_PASS = os.getenv('EMAIL_HOST_PASSWORD')
GMAIL_CREDENTIALS = os.getenv('GMAIL_API_CREDENTIALS')
GMAIL_SCOPES = os.getenv('GMAIL_API_SCOPES', 'https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send')
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN')

MSG91_API_KEY = os.getenv('MSG91_API_KEY')
MSG91_SENDER_EMAIL = os.getenv('MSG91_SENDER_EMAIL', EMAIL_USER or '')
MSG91_EMAIL_ENDPOINT = os.getenv('MSG91_EMAIL_ENDPOINT', 'https://api.msg91.com/api/v5/email/send')
EMAIL_REQUIRE_SUBJECT_KEYWORDS = os.getenv('EMAIL_REQUIRE_SUBJECT_KEYWORDS', 'false').lower() == 'true'

class EmailListenerService:
    """
    Service to listen for emails with bank statements, process them, and reply with reports.
    """

    @staticmethod
    def get_consented_users() -> List[Dict]:
        """Fetch all users who have given consent"""
        db = MongoDB.get_db()
        return list(db[EMAIL_CONSENT_COLLECTION].find({'isActive': True, 'consentGiven': True}))

    @staticmethod
    def connect_gmail():
        try:
            # OAuth 2.0 with read/send scopes
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send'
            ]
            token_uri = 'https://oauth2.googleapis.com/token'
            if not (GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN):
                return None
            creds = Credentials(
                token=None,
                refresh_token=GMAIL_REFRESH_TOKEN,
                token_uri=token_uri,
                client_id=GMAIL_CLIENT_ID,
                client_secret=GMAIL_CLIENT_SECRET,
                scopes=scopes,
            )
            service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
            return service
        except Exception as e:
            logger.error(f"Gmail API initialization failed: {str(e)}")
            return None

    @staticmethod
    def process_inbox(simulation_mode=False):
        """
        Main entry point to check inbox.
        If simulation_mode is True, it doesn't connect to Gmail.
        """
        if simulation_mode:
            logger.info("Running in simulation mode. Skipping real email check.")
            return

        service = EmailListenerService.connect_gmail()
        if not service:
            return

        db = MongoDB.get_db()
        consents = EmailListenerService.get_consented_users()
        if not consents:
            return
        for consent in consents:
            try:
                # Build least-privilege query
                keywords = '(subject:statement OR subject:"account summary" OR subject:"monthly statement")'
                query = f'has:attachment filename:pdf {keywords}'
                allowed = consent.get('allowedSenders', [])
                if allowed:
                    sender_filters = ' OR '.join([f'from:{s}' for s in allowed])
                    query = f'{query} ({sender_filters})'
                messages_list = service.users().messages().list(userId='me', q=query, includeSpamTrash=False).execute()
                msgs = messages_list.get('messages', [])
                if not msgs:
                    continue
                for m in msgs:
                    try:
                        msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
                        headers = msg.get('payload', {}).get('headers', [])
                        hdr = {h['name'].lower(): h['value'] for h in headers}
                        subject = hdr.get('subject', '') or ''
                        sender = hdr.get('from', '') or ''
                        keywords = ['statement', 'account summary', 'monthly statement']
                        if EMAIL_REQUIRE_SUBJECT_KEYWORDS:
                            if not any(k in subject.lower() for k in keywords):
                                continue
                        allowed = consent.get('allowedSenders', [])
                        if allowed:
                            if not any(a.lower() in sender.lower() for a in allowed):
                                continue
                        def _yield_pdfs(payload):
                            stack = [payload]
                            while stack:
                                p = stack.pop()
                                fn = (p.get('filename') or '').lower()
                                body = p.get('body') or {}
                                if fn.endswith('.pdf'):
                                    data = body.get('data')
                                    aid = body.get('attachmentId')
                                    buf = None
                                    if data:
                                        buf = base64.urlsafe_b64decode(data.encode('utf-8'))
                                    elif aid:
                                        att = service.users().messages().attachments().get(userId='me', messageId=m['id'], id=aid).execute()
                                        d = att.get('data')
                                        if d:
                                            buf = base64.urlsafe_b64decode(d.encode('utf-8'))
                                    if buf:
                                        yield p.get('filename') or f"attachment_{m['id']}.pdf", buf
                                for sp in (p.get('parts') or []):
                                    stack.append(sp)
                        payload = msg.get('payload', {}) or {}
                        for fname, content in _yield_pdfs(payload):
                            with tempfile.TemporaryDirectory() as temp_dir:
                                path = os.path.join(temp_dir, fname)
                                with open(path, 'wb') as f:
                                    f.write(content)
                                user_id = consent['userId']
                                result = PDFProcessor.process_pdf_to_mongodb(path, user_id)
                                if result.get('success'):
                                    EmailListenerService._generate_and_send_report(result, path, consent)
                    except Exception as e:
                        logger.error(f"Gmail message processing error: {str(e)}")
                db[EMAIL_CONSENT_COLLECTION].update_one({'_id': consent['_id']}, {'$set': {'lastChecked': datetime.now().isoformat()}})
            except Exception as e:
                logger.error(f"Gmail inbox processing error: {str(e)}")

    @staticmethod
    def _process_single_email(msg, user_consent):
        """Process a single email message"""
        sender = email.utils.parseaddr(msg['From'])[1]
        subject = msg['Subject']
        
        logger.info(f"Processing email from {sender}: {subject}")
        
        # Check keywords
        keywords = ['statement', 'account summary', 'monthly statement']
        if EMAIL_REQUIRE_SUBJECT_KEYWORDS:
            if not any(k in subject.lower() for k in keywords):
                logger.info("Subject does not match keywords. Ignoring.")
                return

        # Extract attachments
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if not filename:
                continue
                
            if not filename.lower().endswith('.pdf'):
                logger.info(f"Skipping non-PDF attachment: {filename}")
                continue
                
            # It's a PDF. Process it.
            logger.info(f"Found PDF attachment: {filename}")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                # Process PDF
                try:
                    user_id = user_consent['userId']
                    result = PDFProcessor.process_pdf_to_mongodb(file_path, user_id)
                    
                    if result.get('success'):
                        # Generate Report
                        EmailListenerService._generate_and_send_report(result, file_path, user_consent)
                    else:
                        logger.error(f"PDF Processing failed for {filename}")
                        
                except Exception as e:
                    logger.error(f"Error processing PDF {filename}: {str(e)}")

    @staticmethod
    def _generate_and_send_report(process_result, original_pdf_path, user_consent):
        """Generate financial report and send back to user"""
        db = MongoDB.get_db()
        
        # Fetch data for summary
        statement_id = ObjectId(process_result['statementId'])
        statement = db[STATEMENTS_COLLECTION].find_one({'_id': statement_id})
        transactions = list(db[TRANSACTIONS_COLLECTION].find({'statement_id': statement_id}))
        
        # Generate AI Summary
        summary = generate_expense_summary(statement, transactions)
        
        # Prepare data for report
        report_data = process_result.copy()
        report_data['summary'] = summary
        
        # Generate PDF Report
        with tempfile.TemporaryDirectory() as temp_dir:
            report_filename = f"Financial_Summary_{datetime.now().strftime('%Y%m%d')}.pdf"
            report_path = os.path.join(temp_dir, report_filename)
            
            ReportGenerator.generate_financial_report(report_data, report_path)
            
            # Send Email
            EmailListenerService._send_email(
                to_email=user_consent['email'],
                subject="Your BankFusion Financial Summary",
                body="Your bank statement has been successfully processed by BankFusion.\nPlease find your financial summary attached.",
                attachment_path=report_path
            )

    @staticmethod
    def _send_email(to_email, subject, body, attachment_path=None):
        """Send email with optional attachment via MSG91 (outbound only)"""
        if not MSG91_API_KEY or not MSG91_SENDER_EMAIL:
            logger.warning("MSG91 not configured. Attempting Gmail send fallback.")
            EmailListenerService._send_email_via_gmail(to_email, subject, body, attachment_path)
            if EMAIL_USER and EMAIL_PASS:
                # If Gmail API not available, SMTP can still work
                EmailListenerService._send_email_via_smtp(to_email, subject, body, attachment_path)
            return

        payload = {
            "to": [{"email": to_email}],
            "from": {"email": MSG91_SENDER_EMAIL},
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
            "Authorization": f"Bearer {MSG91_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(MSG91_EMAIL_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=10)
            if resp.status_code >= 200 and resp.status_code < 300:
                logger.info(f"MSG91: Email sent to {to_email}")
            else:
                logger.error(f"MSG91 send failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"MSG91 request error: {str(e)}")

    @staticmethod
    def _send_email_via_gmail(to_email, subject, body, attachment_path=None):
        """Fallback email send using Gmail API"""
        try:
            service = EmailListenerService.connect_gmail()
            if not service:
                logger.error("Gmail service not available; cannot send email.")
                return

            msg = MIMEMultipart()
            msg['to'] = to_email
            msg['subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            sent = service.users().messages().send(userId='me', body={'raw': raw}).execute()
            if sent and sent.get('id'):
                logger.info(f"Gmail: Email sent to {to_email}")
            else:
                logger.error("Gmail send did not return message id")
        except Exception as e:
            logger.error(f"Gmail send error: {str(e)}")

    @staticmethod
    def _send_email_via_smtp(to_email, subject, body, attachment_path=None):
        """Secondary fallback: SMTP using EMAIL_HOST_USER/PASS (e.g., Gmail App Password)"""
        if not EMAIL_USER or not EMAIL_PASS:
            logger.warning("SMTP not configured (EMAIL_HOST_USER/PASSWORD missing).")
            return
        try:
            msg = EmailMessage()
            msg['From'] = EMAIL_USER
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.set_content(body)

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    data = f.read()
                msg.add_attachment(data, maintype='application', subtype='pdf', filename=os.path.basename(attachment_path))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_USER, EMAIL_PASS)
                smtp.send_message(msg)
            logger.info(f"SMTP: Email sent to {to_email}")
        except Exception as e:
            logger.error(f"SMTP send error: {str(e)}")

    @staticmethod
    def simulate_email_arrival(user_email, pdf_path):
        """
        Simulate an email arrival for testing purposes.
        """
        logger.info(f"Simulating email from {user_email} with attachment {pdf_path}")
        
        # Verify user consent
        db = MongoDB.get_db()
        user_consent = db[EMAIL_CONSENT_COLLECTION].find_one({'email': user_email, 'isActive': True})
        
        if not user_consent:
            logger.error(f"No active consent found for {user_email}")
            return {'success': False, 'message': 'No consent found'}

        try:
            # Process directly
            user_id = user_consent['userId']
            result = PDFProcessor.process_pdf_to_mongodb(pdf_path, user_id)
            
            if result.get('success'):
                EmailListenerService._generate_and_send_report(result, pdf_path, user_consent)
                return {'success': True, 'message': 'Processed and report sent'}
            else:
                return {'success': False, 'message': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            return {'success': False, 'message': str(e)}
