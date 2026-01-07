@echo off
REM Simple Server Startup for Food Delivery Platform

echo ============================================================
echo Food Delivery Platform - Starting Server
echo ============================================================
echo.

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment
    pause
    exit /b 1
)
echo OK - Virtual environment activated
echo.

REM Install dependencies
echo [2/4] Installing dependencies...
pip install -q -r requirements.txt
echo OK - Dependencies checked
echo.

REM Run migrations
echo [3/4] Running migrations...
alembic upgrade head
echo OK - Migrations completed
echo.

REM Create admin
echo [4/4] Creating admin user...
python create_admin.py
echo.

echo ============================================================
echo Starting Uvicorn Server
echo ============================================================
echo.
echo Server will be available at:
echo   - API Docs:  http://localhost:8000/docs
echo   - Dashboard: http://localhost:8000/api/v1/dashboard/
echo.
echo Login: admin@fooddelivery.com / admin123
echo.
echo Press CTRL+C to stop
echo ============================================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause

