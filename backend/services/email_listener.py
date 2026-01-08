import email
import os
import tempfile
import logging
import base64
import json
import re
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
# IMPORTANT: If changing scopes, delete token.json to force re-authentication.
GMAIL_SCOPES = os.getenv('GMAIL_API_SCOPES', 'https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.modify')
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
    _debug_unread_done = False

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
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify"
            ]
            token_uri = 'https://oauth2.googleapis.com/token'
            if not (GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN):
                return None
            
            # Aggressive Sanitization
            # 1. Client ID: Remove quotes, whitespace, protocol prefixes, trailing slashes
            #    Then try to extract the specific pattern [0-9]+-[a-z0-9]+.apps.googleusercontent.com
            clean_client_id = GMAIL_CLIENT_ID.strip().strip("'").strip('"')
            clean_client_id = clean_client_id.replace('http://', '').replace('https://', '').rstrip('/')
            
            # Regex extraction for extra safety (if garbage is attached)
            match = re.search(r'(\d+-[a-z0-9]+\.apps\.googleusercontent\.com)', clean_client_id)
            if match:
                clean_client_id = match.group(1)
            
            # 2. Secret: Remove quotes and whitespace
            clean_secret = GMAIL_CLIENT_SECRET.strip().strip("'").strip('"')
            
            # 3. Refresh Token: Remove quotes and whitespace
            clean_refresh = GMAIL_REFRESH_TOKEN.strip().strip("'").strip('"')
            
            # Log masked credentials for verification
            masked_id = clean_client_id[:10] + "..." + clean_client_id[-10:] if len(clean_client_id) > 20 else "INVALID"
            logger.info(f"Using sanitized Gmail Client ID: {masked_id}")
            
            creds = Credentials(
                token=None,
                refresh_token=clean_refresh,
                token_uri=token_uri,
                client_id=clean_client_id,
                client_secret=clean_secret,
            )
            service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
            
            profile = service.users().getProfile(userId="me").execute()
            logger.info(f"Gmail authenticated as: {profile['emailAddress']}")
            
            creds = service._http.credentials
            logger.info(f"Gmail token scopes: {creds.scopes}")

            return service
        except Exception as e:
            logger.error(f"Gmail API initialization failed: {str(e)}")
            return None

    @staticmethod
    def process_inbox(simulation_mode=False):
        """
        Main entry point to check inbox.
        If simulation_mode is True, it doesn't connect to Gmail.
        Returns a summary dict of actions taken.
        """
        stats = {
            'status': 'success',
            'consented_users': 0,
            'emails_found': 0,
            'emails_processed': 0,
            'pdfs_processed': 0,
            'reports_sent': 0,
            'errors': []
        }

        if simulation_mode:
            logger.info("Running in simulation mode. Skipping real email check.")
            stats['status'] = 'simulation_mode'
            return stats

        service = EmailListenerService.connect_gmail()
        if not service:
            stats['status'] = 'failed'
            stats['errors'].append("Failed to connect to Gmail API")
            return stats

        db = MongoDB.get_db()
        consents = EmailListenerService.get_consented_users()
        stats['consented_users'] = len(consents)
        
        if not consents:
            logger.info("No consented users found. Skipping inbox check.")
            return stats
            
        for consent in consents:
            try:
                # Build least-privilege query
                # Enforce sender restriction: from:gaurimhaisne@gmail.com
                query = (
                    "from:gaurimhaisne@gmail.com "
                    "has:attachment "
                    "filename:pdf "
                    "is:unread"
                )
                # if EMAIL_REQUIRE_SUBJECT_KEYWORDS:
                #     keywords = '(subject:statement OR subject:"account summary" OR subject:"monthly statement")'
                #     query = f'{query} {keywords}'
                
                # Filter by unread to avoid processing old emails repeatedly
                # query += ' is:unread'  # Optional: Uncomment if we only want unread emails

                # allowed = consent.get('allowedSenders', [])
                # if allowed:
                #     sender_filters = ' OR '.join([f'from:{s}' for s in allowed])
                #     query = f'{query} ({sender_filters})'
                
                logger.info(f"Checking Gmail with query: {query}")
                messages_list = service.users().messages().list(userId='me', q=query).execute()
                msgs = messages_list.get('messages', [])
                logger.info(f"Query returned {len(msgs)} messages.")
                stats['emails_found'] += len(msgs)
                
                if not msgs and not EmailListenerService._debug_unread_done:
                    try:
                        dbg = service.users().messages().list(userId='me', q="is:unread").execute()
                        dbg_msgs = dbg.get('messages', [])
                        logger.info(f"[DEBUG] is:unread returned {len(dbg_msgs)} messages")
                        if dbg_msgs:
                            sample_ids = [m['id'] for m in dbg_msgs[:5]]
                            logger.info(f"[DEBUG] Sample unread IDs: {', '.join(sample_ids)}")
                            for sid in sample_ids:
                                try:
                                    dmsg = service.users().messages().get(userId='me', id=sid, format='full').execute()
                                    headers = dmsg.get('payload', {}).get('headers', [])
                                    hdr = {h['name'].lower(): h['value'] for h in headers}
                                    frm = hdr.get('from', '')
                                    subj = hdr.get('subject', '')
                                    payload = dmsg.get('payload', {}) or {}
                                    filenames = []
                                    stack = [payload]
                                    while stack:
                                        p = stack.pop()
                                        fn = (p.get('filename') or '')
                                        if fn:
                                            filenames.append(fn)
                                        for sp in (p.get('parts') or []):
                                            stack.append(sp)
                                    logger.info(f"[DEBUG] Unread sample From='{frm}' Subject='{subj}' Attachments={filenames}")
                                except Exception as de:
                                    logger.error(f"[DEBUG] Failed to inspect unread sample {sid}: {str(de)}")
                            try:
                                subqs = [
                                    "from:gaurimhaisne@gmail.com is:unread",
                                    "has:attachment is:unread",
                                    "filename:pdf is:unread",
                                    "from:gaurimhaisne@gmail.com has:attachment is:unread",
                                    "from:gaurimhaisne@gmail.com filename:pdf is:unread",
                                    "has:attachment filename:pdf is:unread",
                                ]
                                for sq in subqs:
                                    r = service.users().messages().list(userId='me', q=sq).execute()
                                    c = len(r.get('messages', []))
                                    logger.info(f"[DEBUG] Subquery '{sq}' returned {c} messages")
                            except Exception as se:
                                logger.error(f"[DEBUG] Subquery checks failed: {str(se)}")
                        EmailListenerService._debug_unread_done = True
                    except Exception as e:
                        logger.error(f"[DEBUG] is:unread check failed: {str(e)}")
                
                if not msgs:
                    continue

                for m in msgs:
                    stats['emails_processed'] += 1
                    try:
                        msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
                        headers = msg.get('payload', {}).get('headers', [])
                        hdr = {h['name'].lower(): h['value'] for h in headers}
                        subject = hdr.get('subject', '') or ''
                        sender = hdr.get('from', '') or ''
                        
                        logger.info(f"Processing email: Subject='{subject}', Sender='{sender}'")
                        
                        keywords = ['statement', 'account summary', 'monthly statement']
                        if EMAIL_REQUIRE_SUBJECT_KEYWORDS:
                            if not any(k in subject.lower() for k in keywords):
                                logger.info(f"Skipping email '{subject}': Subject keyword mismatch")
                                continue
                        
                        allowed = consent.get('allowedSenders', [])
                        # if allowed:
                        #     if not any(a.lower() in sender.lower() for a in allowed):
                        #         logger.info(f"Skipping email '{subject}': Sender '{sender}' not in allowed list")
                        #         continue
                                
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
                        pdf_count = 0
                        any_success = False
                        for fname, content in _yield_pdfs(payload):
                            pdf_count += 1
                            stats['pdfs_processed'] += 1
                            logger.info(f"PDF found: {fname}")
                            
                            with tempfile.TemporaryDirectory() as temp_dir:
                                path = os.path.join(temp_dir, fname)
                                with open(path, 'wb') as f:
                                    f.write(content)
                                user_id = consent['userId']
                                
                                result = PDFProcessor.process_pdf_to_mongodb(path, user_id)
                                if result.get('success'):
                                    try:
                                        EmailListenerService.generate_and_send_report(result, path, consent.get('email'))
                                        stats['reports_sent'] += 1
                                        any_success = True
                                    except Exception as e:
                                        err = f"Summary generation/email failed for {fname}: {str(e)}"
                                        stats['errors'].append(err)
                                        logger.error(err)
                                else:
                                    err = f"PDF processing failed for {fname}: {result.get('error')}"
                                    stats['errors'].append(err)
                                    logger.error(err)
                        
                        if pdf_count == 0:
                             logger.info(f"No PDF attachments found in email '{subject}'")

                        # Mark message as processed and read ONLY after successful processing + summary email
                        if any_success:
                            db[EMAIL_CONSENT_COLLECTION].update_one(
                                {'_id': consent['_id']},
                                {'$addToSet': {'processedMessageIds': m['id']}}
                            )
                            
                            service.users().messages().modify(
                                userId="me",
                                id=m['id'],
                                body={"removeLabelIds": ["UNREAD"]}
                            ).execute()
                    except Exception as e:
                        err_msg = f"Error processing message {m['id']}: {str(e)}"
                        logger.error(err_msg)
                        stats['errors'].append(err_msg)
                        
                db[EMAIL_CONSENT_COLLECTION].update_one({'_id': consent['_id']}, {'$set': {'lastChecked': datetime.now().isoformat()}})
            except Exception as e:
                err_msg = f"Gmail inbox processing error: {str(e)}"
                logger.error(err_msg)
                stats['errors'].append(err_msg)
        
        return stats

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
            logger.info(f"PDF found: {filename}")
            
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
                        EmailListenerService.generate_and_send_report(result, file_path, user_consent)
                    else:
                        logger.error(f"PDF Processing failed for {filename}")
                        
                except Exception as e:
                    logger.error(f"Error processing PDF {filename}: {str(e)}")

    @staticmethod
    def generate_and_send_report(process_result, original_pdf_path, user_consent):
        """
        Generate financial report and send back to user.
        user_consent can be a dict (from DB) or a string (email address).
        This method is static to avoid instantiation issues.
        """
        db = MongoDB.get_db()
        
        # Determine email address
        if isinstance(user_consent, str):
            to_email = user_consent
        else:
            to_email = user_consent.get('email')
            
        if not to_email:
            logger.error("Cannot send report: No email address provided")
            return
            
        logger.info(f"Report generation triggered for {to_email}")
        
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
                to_email=to_email,
                subject="Your BankFusion Financial Summary",
                body="Your bank statement has been successfully processed by BankFusion.\nPlease find your financial summary attached.",
                attachment_path=report_path
            )

    @staticmethod
    def _send_email(to_email, subject, body, attachment_path=None):
        """Send email using the configured provider (SendGrid/MSG91) with fallback"""
        from services.email_providers import get_email_provider
        
        try:
            provider = get_email_provider()
            if provider.send_email(to_email, subject, body, attachment_path):
                return
            
            logger.warning("Primary email provider failed. Attempting Gmail send fallback.")
        except Exception as e:
            logger.error(f"Error using email provider: {str(e)}")
            logger.warning("Attempting Gmail send fallback.")
            
        EmailListenerService._send_email_via_gmail(to_email, subject, body, attachment_path)
        if EMAIL_USER and EMAIL_PASS:
            # If Gmail API not available, SMTP can still work
            EmailListenerService._send_email_via_smtp(to_email, subject, body, attachment_path)

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
                EmailListenerService.generate_and_send_report(result, pdf_path, user_consent.get('email'))
                return {'success': True, 'message': 'Processed and report sent'}
            else:
                return {'success': False, 'message': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            return {'success': False, 'message': str(e)}
