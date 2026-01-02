#!/bin/bash
# BankFusion Flask API - Virtual Environment Activation Script (Linux/Mac)
# This script activates the virtual environment and verifies setup

echo "======================================================================"
echo "BankFusion Flask API - Activating Virtual Environment"
echo "======================================================================"
echo ""

# Check if .venv exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo ""
    echo "Please create it first:"
    echo "  python -m venv .venv"
    echo ""
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

echo "[OK] Virtual environment activated"
echo ""

# Verify Python is from venv
python --version
echo ""

# Check if dependencies are installed
echo "[CHECK] Verifying dependencies..."
python -c "import flask; import flask_cors; import pymongo; from dotenv import load_dotenv; print('[OK] All dependencies available')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARN] Some dependencies may be missing"
    echo ""
    echo "Installing dependencies..."
    python -m pip install -r requirements.txt
fi

echo ""
echo "======================================================================"
echo "[SUCCESS] Virtual environment ready!"
echo "======================================================================"
echo ""
echo "You can now run:"
echo "  python app.py"
echo ""
echo "To deactivate, type: deactivate"
echo "======================================================================"
echo ""

# Keep shell open (interactive mode)
exec $SHELL

