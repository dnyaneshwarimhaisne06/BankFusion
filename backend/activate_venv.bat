@echo off
REM BankFusion Flask API - Virtual Environment Activation Script (Windows)
REM This script activates the virtual environment and verifies setup

echo ======================================================================
echo BankFusion Flask API - Activating Virtual Environment
echo ======================================================================
echo.

REM Check if .venv exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please create it first:
    echo   python -m venv .venv
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

echo [OK] Virtual environment activated
echo.

REM Verify Python is from venv
python --version
echo.

REM Check if dependencies are installed
echo [CHECK] Verifying dependencies...
python -c "import flask; import flask_cors; import pymongo; from dotenv import load_dotenv; print('[OK] All dependencies available')" 2>nul
if errorlevel 1 (
    echo [WARN] Some dependencies may be missing
    echo.
    echo Installing dependencies...
    python -m pip install -r requirements.txt
)

echo.
echo ======================================================================
echo [SUCCESS] Virtual environment ready!
echo ======================================================================
echo.
echo You can now run:
echo   python app.py
echo.
echo To deactivate, type: deactivate
echo ======================================================================
echo.

cmd /k

