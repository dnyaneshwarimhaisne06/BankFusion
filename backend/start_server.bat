@echo off
REM BankFusion Flask API - Quick Start Script
echo ======================================================================
echo Starting BankFusion Flask Backend Server
echo ======================================================================
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] Virtual environment not found. Using system Python...
    echo.
)

echo [INFO] Starting Flask server on http://localhost:5000
echo [INFO] Press Ctrl+C to stop the server
echo ======================================================================
echo.

python app.py

pause

