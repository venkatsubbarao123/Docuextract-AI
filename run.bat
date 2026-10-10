@echo off
title DocuExtract AI - Document Extraction Agent Launcher
echo ====================================================================
echo             DocuExtract AI - Document Extraction Agent
echo ====================================================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in the PATH environment variable.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

echo Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Dependency installation failed or some packages had conflicts.
    echo Trying to proceed anyway...
)
echo.

echo Launching web browser dashboard at http://127.0.0.1:8008...
start "" "http://127.0.0.1:8008"
echo.

echo Starting FastAPI server via uvicorn...
echo [INFO] Press Ctrl+C in this terminal window to stop the server.
echo.
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8008

pause
