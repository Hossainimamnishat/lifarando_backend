"""
Create Super Admin User
Run this after the database is set up and migrations are complete.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import async_session
from app.models.user import User
from app.models.rbac import Role, UserRole
from app.core.security import get_password_hash


async def create_super_admin():
    """Create a super admin user with full platform access"""

    print("=" * 60)
    print("Creating Super Admin User...")
    print("=" * 60)
    print()

    try:
        async with async_session() as session:
            # Check if super admin role exists
            from sqlalchemy import select

            result = await session.execute(
                select(Role).where(Role.code == "SUPER_ADMIN")
            )
            role = result.scalar_one_or_none()

            if not role:
                # Create SUPER_ADMIN role
                print("Creating SUPER_ADMIN role...")
                role = Role(
                    code="SUPER_ADMIN",
                    name="Super Administrator",
                    scope_type="GLOBAL",
                    description="Full platform access - can manage everything"
                )
                session.add(role)
                await session.flush()
                print("✓ SUPER_ADMIN role created")
            else:
                print("✓ SUPER_ADMIN role already exists")

            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.email == "admin@fooddelivery.com")
            )
            admin = result.scalar_one_or_none()

            if not admin:
                # Create super admin user
                print("\nCreating admin user...")
                admin = User(
                    email="admin@fooddelivery.com",
                    username="superadmin",
                    hashed_password=get_password_hash("admin123"),
                    full_name="Super Administrator",
                    phone="+1234567890",
                    is_active=True,
                    is_verified=True
                )
                session.add(admin)
                await session.flush()
                print("✓ Admin user created")
            else:
                print("\n✓ Admin user already exists")

            # Check if role assignment exists
            result = await session.execute(
                select(UserRole).where(
                    UserRole.user_id == admin.id,
                    UserRole.role_id == role.id
                )
            )
            user_role = result.scalar_one_or_none()

            if not user_role:
                # Assign role to user
                print("\nAssigning SUPER_ADMIN role to user...")
                user_role = UserRole(
                    user_id=admin.id,
                    role_id=role.id,
                    is_active=True
                )
                session.add(user_role)
                print("✓ Role assigned")
            else:
                print("\n✓ Role already assigned")

            await session.commit()

            print()
            print("=" * 60)
            print("✅ SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("Super Admin Credentials:")
            print("-" * 60)
            print(f"  Email:    admin@fooddelivery.com")
            print(f"  Username: superadmin")
            print(f"  Password: admin123")
            print("-" * 60)
            print()
            print("You can now:")
            print("  1. Login at: http://localhost:8000/docs")
            print("  2. Use /api/v1/auth/login endpoint")
            print("  3. Access dashboard: http://localhost:8000/api/v1/dashboard/")
            print()
            print("⚠️  IMPORTANT: Change the password after first login!")
            print()

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR:")
        print("=" * 60)
        print(f"{e}")
        print()
        print("Make sure:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'fooddelivery' exists")
        print("  3. Migrations have been run: alembic upgrade head")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def create_sample_roles():
    """Create additional role types for the system"""

    print("\nCreating additional role types...")
    print("-" * 60)

    roles_to_create = [
        {
            "code": "CITY_ADMIN",
            "name": "City Administrator",
            "scope_type": "CITY",
            "description": "Manages all operations within a city"
        },
        {
            "code": "DISPATCHER",
            "name": "Dispatcher",
            "scope_type": "CITY",
            "description": "Assigns and manages riders in a city"
        },
        {
            "code": "SUPPORT",
            "name": "Support Agent",
            "scope_type": "CITY",
            "description": "Handles customer support for a city"
        },
        {
            "code": "SHIFT_LEAD",
            "name": "Shift Lead",
            "scope_type": "CITY",
            "description": "Manages rider shifts and schedules"
        },
        {
            "code": "RESTAURANT_ADMIN",
            "name": "Restaurant Administrator",
            "scope_type": "RESTAURANT",
            "description": "Manages a specific restaurant"
        },
        {
            "code": "RIDER",
            "name": "Delivery Rider",
            "scope_type": "SELF",
            "description": "Delivery rider - access to own data only"
        },
        {
            "code": "CUSTOMER",
            "name": "Customer",
            "scope_type": "SELF",
            "description": "Customer - access to own orders only"
        }
    ]

    try:
        async with async_session() as session:
            from sqlalchemy import select

            for role_data in roles_to_create:
                result = await session.execute(
                    select(Role).where(Role.code == role_data["code"])
                )
                role = result.scalar_one_or_none()

                if not role:
                    role = Role(**role_data)
                    session.add(role)
                    print(f"  ✓ Created role: {role_data['name']}")
                else:
                    print(f"  ✓ Role already exists: {role_data['name']}")

            await session.commit()
            print()
            print("✓ All role types created successfully!")

    except Exception as e:
        print(f"\n❌ Error creating roles: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    asyncio.run(create_super_admin())
    asyncio.run(create_sample_roles())
    print()

