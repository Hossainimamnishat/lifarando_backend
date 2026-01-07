"""
Test PostgreSQL Database Connection

This script verifies that:
1. PostgreSQL is running
2. Database exists
3. Connection works
4. Tables are created (if migrations ran)
"""
import asyncio
import sys
from sqlalchemy import text
from app.db.session import async_session


async def test_connection():
    print("=" * 60)
    print("PostgreSQL Connection Test")
    print("=" * 60)
    print()

    try:
        # Test connection
        print("📡 Testing database connection...")
        async with async_session() as session:
            # Get PostgreSQL version
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected successfully!")
            print(f"✅ PostgreSQL Version: {version.split(',')[0]}")
            print()

            # Check database name
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"✅ Current Database: {db_name}")
            print()

            # List tables
            print("📊 Checking tables...")
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public'
                ORDER BY table_name
            """))
            tables = result.fetchall()

            if tables:
                print(f"✅ Found {len(tables)} tables:")
                for i, (table_name,) in enumerate(tables, 1):
                    print(f"   {i:2d}. {table_name}")
                print()

                # Check roles table
                print("🛡️  Checking RBAC setup...")
                result = await session.execute(text("SELECT COUNT(*) FROM roles"))
                role_count = result.scalar()

                if role_count > 0:
                    print(f"✅ Found {role_count} roles in database")

                    # List roles
                    result = await session.execute(text("""
                        SELECT code, name, scope_type 
                        FROM roles 
                        ORDER BY code
                    """))
                    roles = result.fetchall()

                    print("\nAvailable Roles:")
                    for code, name, scope_type in roles:
                        print(f"   • {code:20s} - {name:30s} ({scope_type})")
                    print()
                else:
                    print("⚠️  No roles found. Migrations may not have run.")
                    print("   Run: alembic upgrade head")
                    print()

                # Check cities
                result = await session.execute(text("SELECT COUNT(*) FROM cities"))
                city_count = result.scalar()
                print(f"🌆 Cities: {city_count}")

                # Check users
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"👥 Users: {user_count}")

                # Check restaurants
                result = await session.execute(text("SELECT COUNT(*) FROM restaurants"))
                restaurant_count = result.scalar()
                print(f"🏪 Restaurants: {restaurant_count}")

                # Check orders
                result = await session.execute(text("SELECT COUNT(*) FROM orders"))
                order_count = result.scalar()
                print(f"📦 Orders: {order_count}")

            else:
                print("⚠️  No tables found!")
                print("   This means migrations haven't been run yet.")
                print("   Run: alembic upgrade head")

            print()
            print("=" * 60)
            print("✅ Database is ready!")
            print("=" * 60)
            print()
            print("Next steps:")
            print("1. If no tables found: alembic upgrade head")
            print("2. Start server: uvicorn app.main:app --reload")
            print("3. Access API: http://localhost:8000/docs")
            print()

            return True

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Connection Failed!")
        print("=" * 60)
        print()
        print(f"Error: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Check if PostgreSQL is running:")
        print("   docker ps  (for Docker)")
        print("   Get-Service postgresql*  (for Windows service)")
        print()
        print("2. Verify database exists:")
        print("   docker exec fooddelivery-postgres psql -U postgres -l")
        print()
        print("3. Check .env file has correct DATABASE_URL:")
        print("   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fooddelivery")
        print()
        print("4. If using Docker, ensure container is running:")
        print("   docker start fooddelivery-postgres")
        print()

        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)

