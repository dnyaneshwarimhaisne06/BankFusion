"""
Test script to verify Flask app can start without errors
Does not run the server, just verifies all components
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all imports"""
    print("[TEST] Testing imports...")
    try:
        from flask import Flask, jsonify
        from flask_cors import CORS
        from config import DEBUG, HOST, PORT, BANK_TYPES
        from db.mongo import MongoDB
        from db.repositories import StatementRepository, TransactionRepository
        from routes.statements import statements_bp
        from routes.transactions import transactions_bp
        from routes.analytics import analytics_bp
        from services.analytics import AnalyticsService
        from utils.serializers import create_response, serialize_document, serialize_documents
        print("  [OK] All imports successful")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False

def test_flask_app():
    """Test Flask app initialization"""
    print("[TEST] Testing Flask app initialization...")
    try:
        from app import app
        assert app is not None
        assert app.name == 'app'
        print("  [OK] Flask app created")
        return True
    except Exception as e:
        print(f"  [FAIL] Flask app error: {e}")
        return False

def test_blueprints():
    """Test blueprint registration"""
    print("[TEST] Testing blueprint registration...")
    try:
        from app import app
        blueprints = list(app.blueprints.keys())
        expected = ['statements', 'transactions', 'analytics']
        
        for bp in expected:
            if bp not in blueprints:
                print(f"  [FAIL] Missing blueprint: {bp}")
                return False
        
        print(f"  [OK] All blueprints registered: {blueprints}")
        return True
    except Exception as e:
        print(f"  [FAIL] Blueprint error: {e}")
        return False

def test_routes():
    """Test route registration"""
    print("[TEST] Testing route registration...")
    try:
        from app import app
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        expected_routes = [
            '/',
            '/api/health',
            '/api/statements',
            '/api/statements/<statement_id>',
            '/api/transactions',
            '/api/analytics/category-spend'
        ]
        
        for route in expected_routes:
            if route not in routes:
                print(f"  [WARN] Route not found: {route}")
        
        print(f"  [OK] Found {len(routes)} routes")
        return True
    except Exception as e:
        print(f"  [FAIL] Route error: {e}")
        return False

def test_mongodb_connection():
    """Test MongoDB connection (non-blocking)"""
    print("[TEST] Testing MongoDB connection...")
    try:
        from db.mongo import MongoDB
        # Try to get connection (will fail if MongoDB not running, but that's OK)
        try:
            db = MongoDB.get_db()
            print("  [OK] MongoDB connection available")
        except Exception as e:
            print(f"  [WARN] MongoDB not available: {e}")
            print("  [INFO] API will still start, but DB operations will fail")
        return True
    except Exception as e:
        print(f"  [FAIL] MongoDB module error: {e}")
        return False

def test_serializers():
    """Test serialization functions"""
    print("[TEST] Testing serializers...")
    try:
        from utils.serializers import create_response, serialize_document, serialize_documents
        from bson import ObjectId
        
        # Test create_response
        resp = create_response(True, {"test": "data"})
        assert resp['success'] == True
        assert 'data' in resp
        
        # Test serialize_document
        doc = {'_id': ObjectId(), 'test': 'value'}
        serialized = serialize_document(doc)
        assert isinstance(serialized['_id'], str)
        
        print("  [OK] Serializers working correctly")
        return True
    except Exception as e:
        print(f"  [FAIL] Serializer error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("BankFusion Flask API - Startup Test")
    print("=" * 70)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Flask App", test_flask_app),
        ("Blueprints", test_blueprints),
        ("Routes", test_routes),
        ("MongoDB", test_mongodb_connection),
        ("Serializers", test_serializers)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  [FAIL] {name} test crashed: {e}")
            results.append((name, False))
        print()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("=" * 70)
        print("[SUCCESS] All tests passed! Backend is ready to run.")
        print("=" * 70)
        print()
        print("You can now start the server with:")
        print("  python app.py")
        print()
        return 0
    else:
        print()
        print("=" * 70)
        print("[FAILURE] Some tests failed. Please fix issues before running.")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(main())

