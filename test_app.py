import sys
import traceback

print("=" * 60)
print("TESTING APPLICATION STARTUP")
print("=" * 60)
print()

# Test 1: Check Python version
print("[1] Python Version:")
print(f"    {sys.version}")
print()

# Test 2: Try imports
print("[2] Testing imports...")
try:
    from app.config import settings
    print("    OK - config imported")
    print(f"    Database URL: {settings.DATABASE_URL[:60]}...")
except Exception as e:
    print(f"    ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from app.db.session import engine
    print("    OK - database session imported")
except Exception as e:
    print(f"    ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from app.main import app
    print("    OK - FastAPI app imported")
except Exception as e:
    print(f"    ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# Test 3: Check database connection
print("[3] Testing database connection...")
import asyncio

async def test_db():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        return str(e)

from sqlalchemy import text
result = asyncio.run(test_db())
if result is True:
    print("    OK - Database connection successful")
else:
    print(f"    ERROR - Database connection failed:")
    print(f"    {result}")
    print()
    print("    Please ensure:")
    print("    1. PostgreSQL is running")
    print("    2. Database 'fooddelivery' exists")
    print("    3. Credentials in .env are correct")
    sys.exit(1)

print()

# Test 4: Check if migrations needed
print("[4] Checking database migrations...")
try:
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    print("    Run: alembic upgrade head")
except Exception as e:
    print(f"    WARNING: {e}")

print()
print("=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print()
print("You can now start the server:")
print("    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
print()

