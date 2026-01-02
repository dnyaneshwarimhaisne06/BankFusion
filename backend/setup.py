"""
Setup script for BankFusion Flask API
Ensures virtual environment is activated and dependencies are installed
"""

import sys
import subprocess
import os
from pathlib import Path

def check_venv():
    """Check if virtual environment is activated"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("=" * 70)
        print("ERROR: Virtual environment is NOT activated!")
        print("=" * 70)
        print("\nPlease activate the virtual environment first:")
        print("  Windows:  .venv\\Scripts\\activate")
        print("  Linux/Mac: source .venv/bin/activate")
        print("\nOr run: python setup.py")
        print("=" * 70)
        return False
    
    print(f"[OK] Virtual environment active: {sys.prefix}")
    return True

def install_dependencies():
    """Install dependencies from requirements.txt"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"[ERROR] requirements.txt not found: {requirements_file}")
        return False
    
    print(f"\n[INSTALL] Installing dependencies from {requirements_file}")
    print("-" * 70)
    
    try:
        # Use python -m pip to ensure we use the venv's pip
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("[OK] Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install dependencies:")
        print(e.stderr)
        return False

def verify_imports():
    """Verify all required modules can be imported"""
    print("\n[VERIFY] Verifying imports...")
    print("-" * 70)
    
    modules = [
        'flask',
        'flask_cors',
        'pymongo',
        'dotenv',
        'bson'
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError as e:
            print(f"  [FAIL] {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n[ERROR] Failed to import: {', '.join(failed)}")
        return False
    
    print("\n[OK] All modules imported successfully")
    return True

def verify_app():
    """Verify Flask app can be imported"""
    print("\n[VERIFY] Verifying Flask app...")
    print("-" * 70)
    
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        from app import app
        print("[OK] Flask app imported successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to import Flask app: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main setup function"""
    print("=" * 70)
    print("BankFusion Flask API - Setup")
    print("=" * 70)
    
    # Check venv
    if not check_venv():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Verify imports
    if not verify_imports():
        sys.exit(1)
    
    # Verify app
    if not verify_app():
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("[SUCCESS] Setup complete! You can now run: python app.py")
    print("=" * 70)

if __name__ == '__main__':
    main()

