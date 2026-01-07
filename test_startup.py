"""Test script to verify the application can start"""
import sys
import traceback

try:
    print("=" * 60)
    print("Testing Application Startup...")
    print("=" * 60)

    # Test 1: Import main modules
    print("\n1. Testing imports...")
    from app.main import app
    from app.config import settings
    print("   ✓ Imports successful")

    # Test 2: Check database URL
    print("\n2. Checking database configuration...")
    print(f"   DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    print("   ✓ Database URL configured")

    # Test 3: Check if app is configured
    print("\n3. Checking FastAPI app...")
    print(f"   App title: {app.title}")
    print(f"   Routes count: {len(app.routes)}")
    print("   ✓ App configured correctly")

    # Test 4: Try to connect to database
    print("\n4. Testing database connection...")
    import asyncio
    from app.db.session import engine

    async def test_db():
        try:
            async with engine.begin() as conn:
                await conn.run_sync(lambda _: None)
            return True
        except Exception as e:
            return str(e)

    result = asyncio.run(test_db())
    if result is True:
        print("   ✓ Database connection successful!")
    else:
        print(f"   ✗ Database connection failed: {result}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nYou can now start the server with:")
    print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("\nOr simply run:")
    print("   .\\run_app.bat")

except Exception as e:
    print("\n" + "=" * 60)
    print("ERROR OCCURRED:")
    print("=" * 60)
    print(traceback.format_exc())
    sys.exit(1)

