@echo off
REM Complete Application Startup Script
REM This script will set up and run your Food Delivery Platform

echo ============================================================
echo Food Delivery Platform - Complete Startup
echo ============================================================
echo.

REM Step 1: Check if virtual environment is activated
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python or activate your virtual environment
    pause
    exit /b 1
)

echo Step 1: Checking Python environment...
python --version
echo.

REM Step 2: Install/Update dependencies
echo Step 2: Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
)
echo.

REM Step 3: Run database migrations
echo Step 3: Running database migrations...
alembic upgrade head
if errorlevel 1 (
    echo WARNING: Migrations may have failed
    echo This is normal if tables already exist
)
echo.

REM Step 4: Create admin user
echo Step 4: Creating super admin user (if not exists)...
python create_admin.py
echo.

REM Step 5: Start the application
echo ============================================================
echo Starting Application Server...
echo ============================================================
echo.
echo Server will be available at:
echo   - Local: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo   - Dashboard: http://localhost:8000/api/v1/dashboard/
echo.
echo Login Credentials:
echo   - Email: admin@fooddelivery.com
echo   - Password: admin123
echo.
echo Press CTRL+C to stop the server
echo ============================================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause

