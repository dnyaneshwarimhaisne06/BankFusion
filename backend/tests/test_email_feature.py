import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

# Need to mock imports that might fail if dependencies aren't perfect in test env
sys.modules['reportlab'] = MagicMock()
sys.modules['reportlab.lib'] = MagicMock()
sys.modules['reportlab.lib.pagesizes'] = MagicMock()
sys.modules['reportlab.platypus'] = MagicMock()
sys.modules['reportlab.lib.styles'] = MagicMock()

# Mock bson
mock_bson = MagicMock()
mock_bson.ObjectId = MagicMock
sys.modules['bson'] = mock_bson

# Mock other dependencies
mock_pymongo = MagicMock()
mock_pymongo.errors = MagicMock()
sys.modules['pymongo'] = mock_pymongo
sys.modules['pymongo.errors'] = mock_pymongo.errors

sys.modules['pdfplumber'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['flask'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['requests'] = MagicMock()

from services.email_listener import EmailListenerService

class TestEmailFeature(unittest.TestCase):
    @patch('services.email_listener.MongoDB')
    @patch('services.email_listener.PDFProcessor')
    @patch('services.email_listener.EmailListenerService._generate_and_send_report')
    def test_simulate_email_arrival_success(self, mock_send, mock_pdf, mock_mongo):
        # Setup mocks
        mock_db = MagicMock()
        mock_mongo.get_db.return_value = mock_db
        
        # Mock consent finding
        # We need to access the collection by name, which is 'email_consents'
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {
            'userId': 'test_user',
            'email': 'test@example.com',
            'isActive': True
        }
        
        # Mock PDF processing success
        mock_pdf.process_pdf_to_mongodb.return_value = {
            'success': True,
            'statementId': '123'
        }
        
        # Run simulation
        result = EmailListenerService.simulate_email_arrival('test@example.com', 'dummy.pdf')
        
        # Verify
        self.assertTrue(result['success'])
        mock_pdf.process_pdf_to_mongodb.assert_called_once()
        mock_send.assert_called_once()

    @patch('services.email_listener.MongoDB')
    def test_simulate_email_no_consent(self, mock_mongo):
        # Setup mocks
        mock_db = MagicMock()
        mock_mongo.get_db.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = None
        
        # Run simulation
        result = EmailListenerService.simulate_email_arrival('test@example.com', 'dummy.pdf')
        
        # Verify
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'No consent found')

if __name__ == '__main__':
    unittest.main()
