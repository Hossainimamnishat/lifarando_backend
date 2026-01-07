"""Add RBAC tables - roles, user_roles, cities, shift_leads

Revision ID: rbac_001
Revises:
Create Date: 2026-01-06

This migration adds comprehensive RBAC support with:
- roles table (role definitions)
- user_roles table (user role assignments with scope)
- cities table (geographic zones)
- shift_leads table (shift lead constraints)
- Updates to restaurants, orders for city_id and approval workflow
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'rbac_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create scope_type enum
    scope_type_enum = postgresql.ENUM(
        'global', 'city', 'restaurant', 'self',
        name='scopetype',
        create_type=False
    )
    scope_type_enum.create(op.get_bind(), checkfirst=True)

    # Create cities table
    op.create_table(
        'cities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_cities_name', 'cities', ['name'])

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('scope_type', scope_type_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_roles_code', 'roles', ['code'])

    # Add city_id to restaurants (if not exists)
    with op.batch_alter_table('restaurants') as batch_op:
        batch_op.add_column(sa.Column('city_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('approved_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('cuisine_type', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('description', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

        batch_op.create_foreign_key('fk_restaurants_city', 'cities', ['city_id'], ['id'])
        batch_op.create_foreign_key('fk_restaurants_owner', 'users', ['owner_id'], ['id'])
        batch_op.create_foreign_key('fk_restaurants_approver', 'users', ['approved_by'], ['id'])

        batch_op.create_index('idx_restaurants_city_active', ['city_id', 'is_active'])
        batch_op.create_index('idx_restaurants_owner', ['owner_id'])
        batch_op.create_index('idx_restaurants_approved', ['is_approved', 'is_active'])

    # Add city_id and rider_id to orders (if not exists)
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('city_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rider_id', sa.Integer(), nullable=True))

        batch_op.create_foreign_key('fk_orders_city', 'cities', ['city_id'], ['id'])
        batch_op.create_foreign_key('fk_orders_rider', 'users', ['rider_id'], ['id'])

        batch_op.create_index('idx_orders_city_status', ['city_id', 'status'])
        batch_op.create_index('idx_orders_restaurant_status', ['restaurant_id', 'status'])
        batch_op.create_index('idx_orders_rider_status', ['rider_id', 'status'])
        batch_op.create_index('idx_orders_customer', ['customer_id', 'created_at'])

    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.Integer(), nullable=True),
        sa.Column('restaurant_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.UniqueConstraint('user_id', 'role_id', 'city_id', 'restaurant_id', name='uq_user_role_scope'),
        sa.CheckConstraint(
            """
            (
                (city_id IS NULL AND restaurant_id IS NULL)
                OR
                (city_id IS NOT NULL AND restaurant_id IS NULL)
                OR
                (restaurant_id IS NOT NULL)
            )
            """,
            name='ck_user_role_scope_valid'
        )
    )
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])
    op.create_index('ix_user_roles_city_id', 'user_roles', ['city_id'])
    op.create_index('ix_user_roles_restaurant_id', 'user_roles', ['restaurant_id'])
    op.create_index('idx_user_roles_user_active', 'user_roles', ['user_id', 'is_active'])
    op.create_index('idx_user_roles_city', 'user_roles', ['city_id', 'is_active'])
    op.create_index('idx_user_roles_restaurant', 'user_roles', ['restaurant_id', 'is_active'])

    # Create shift_leads table
    op.create_table(
        'shift_leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.Integer(), nullable=False),
        sa.Column('min_hours_per_shift', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('max_hours_per_shift', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('min_hours_per_week', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('max_hours_per_week', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'city_id', name='uq_shift_lead_user_city')
    )
    op.create_index('ix_shift_leads_user_id', 'shift_leads', ['user_id'])
    op.create_index('ix_shift_leads_city_id', 'shift_leads', ['city_id'])
    op.create_index('idx_shift_leads_city_active', 'shift_leads', ['city_id', 'is_active'])

    # Insert default roles
    op.execute("""
        INSERT INTO roles (code, name, description, scope_type, is_active) VALUES
        ('super_admin', 'Super Admin', 'Full system access across all cities and restaurants', 'global', true),
        ('city_admin', 'City Admin', 'Manage operations within assigned cities', 'city', true),
        ('shift_lead', 'Shift Lead', 'Manage driver work hours and schedules within a city', 'city', true),
        ('dispatcher', 'Dispatcher', 'Assign and manage deliveries within assigned cities', 'city', true),
        ('support', 'Support', 'Customer support access for assigned cities', 'city', true),
        ('restaurant_admin', 'Restaurant Admin', 'Approve and manage restaurants', 'restaurant', true),
        ('customer', 'Customer', 'Place and track orders', 'self', true),
        ('rider', 'Rider', 'Accept and complete deliveries', 'self', true),
        ('restaurant_owner', 'Restaurant Owner', 'Manage own restaurant', 'self', true)
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('shift_leads')
    op.drop_table('user_roles')

    # Remove columns from orders
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_constraint('fk_orders_city', type_='foreignkey')
        batch_op.drop_constraint('fk_orders_rider', type_='foreignkey')
        batch_op.drop_index('idx_orders_city_status')
        batch_op.drop_index('idx_orders_restaurant_status')
        batch_op.drop_index('idx_orders_rider_status')
        batch_op.drop_index('idx_orders_customer')
        batch_op.drop_column('city_id')
        batch_op.drop_column('rider_id')

    # Remove columns from restaurants
    with op.batch_alter_table('restaurants') as batch_op:
        batch_op.drop_constraint('fk_restaurants_city', type_='foreignkey')
        batch_op.drop_constraint('fk_restaurants_owner', type_='foreignkey')
        batch_op.drop_constraint('fk_restaurants_approver', type_='foreignkey')
        batch_op.drop_index('idx_restaurants_city_active')
        batch_op.drop_index('idx_restaurants_owner')
        batch_op.drop_index('idx_restaurants_approved')
        batch_op.drop_column('city_id')
        batch_op.drop_column('owner_id')
        batch_op.drop_column('is_approved')
        batch_op.drop_column('approved_by')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('cuisine_type')
        batch_op.drop_column('description')
        batch_op.drop_column('rating')
        batch_op.drop_column('created_at')
        batch_op.drop_column('updated_at')

    op.drop_table('roles')
    op.drop_table('cities')

    # Drop enum
    sa.Enum(name='scopetype').drop(op.get_bind(), checkfirst=True)

