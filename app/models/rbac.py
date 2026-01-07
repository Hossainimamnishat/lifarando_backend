"""
RBAC Models - Role-Based Access Control with Scoping

This module defines the core RBAC models for the system with support for:
- GLOBAL scope (Super Admin)
- CITY scope (City Admin, Dispatcher, Support, Shift Lead)
- RESTAURANT scope (Restaurant Admin)
- SELF scope (Customer, Rider - only their own data)
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, ForeignKey, Boolean, DateTime, Index, CheckConstraint, UniqueConstraint
from app.db.base import Base
import enum


class ScopeType(str, enum.Enum):
    """Scope types for role-based access control"""
    GLOBAL = "global"          # Access to everything (Super Admin)
    CITY = "city"              # Access to specific city data
    RESTAURANT = "restaurant"  # Access to specific restaurant data
    SELF = "self"              # Access to only own data


class RoleCode(str, enum.Enum):
    """Predefined role codes for the system"""
    # Global roles
    SUPER_ADMIN = "super_admin"

    # City-scoped roles
    CITY_ADMIN = "city_admin"
    SHIFT_LEAD = "shift_lead"      # Manages driver shifts within a city
    DISPATCHER = "dispatcher"       # Assigns/reassigns riders
    SUPPORT = "support"             # Customer support access

    # Restaurant-scoped roles
    RESTAURANT_ADMIN = "restaurant_admin"

    # Self-scoped roles (legacy compatibility)
    CUSTOMER = "customer"
    RIDER = "rider"
    RESTAURANT_OWNER = "restaurant_owner"


class Role(Base):
    """
    Role definition table - stores available roles in the system
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    scope_type: Mapped[ScopeType] = mapped_column(Enum(ScopeType), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="role")

    def __repr__(self):
        return f"<Role {self.code} ({self.scope_type})>"


class UserRole(Base):
    """
    User-Role assignment table with scope constraints

    A user can have multiple roles with different scopes:
    - User A: Support for City 1, Dispatcher for City 2
    - User B: Restaurant Admin for Restaurant 5
    - User C: Super Admin (global access)

    Constraints:
    - GLOBAL roles: must NOT have city_id or restaurant_id
    - CITY roles: must have city_id, must NOT have restaurant_id
    - RESTAURANT roles: must have restaurant_id (city_id optional but recommended)
    - SELF roles: must NOT have city_id or restaurant_id
    """
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scope fields
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    restaurant_id: Mapped[int | None] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), index=True)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")
    city: Mapped["City | None"] = relationship("City", foreign_keys=[city_id])
    restaurant: Mapped["Restaurant | None"] = relationship("Restaurant", foreign_keys=[restaurant_id])
    assigner: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        # Unique constraint: user can't have the same role+scope combination twice
        UniqueConstraint('user_id', 'role_id', 'city_id', 'restaurant_id', name='uq_user_role_scope'),

        # Check constraints for scope validation
        CheckConstraint(
            """
            (
                -- GLOBAL roles: no scope fields
                (city_id IS NULL AND restaurant_id IS NULL)
                OR
                -- CITY roles: city_id required, no restaurant_id
                (city_id IS NOT NULL AND restaurant_id IS NULL)
                OR
                -- RESTAURANT roles: restaurant_id required
                (restaurant_id IS NOT NULL)
            )
            """,
            name='ck_user_role_scope_valid'
        ),

        # Indexes for performance
        Index('idx_user_roles_user_active', 'user_id', 'is_active'),
        Index('idx_user_roles_city', 'city_id', 'is_active'),
        Index('idx_user_roles_restaurant', 'restaurant_id', 'is_active'),
    )

    def __repr__(self):
        scope_info = []
        if self.city_id:
            scope_info.append(f"city={self.city_id}")
        if self.restaurant_id:
            scope_info.append(f"restaurant={self.restaurant_id}")
        scope_str = f"[{', '.join(scope_info)}]" if scope_info else "[global]"
        return f"<UserRole user={self.user_id} role={self.role_id} {scope_str}>"


class City(Base):
    """
    City/Zone model for geographic scoping
    """
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<City {self.name} ({self.code})>"


class ShiftLead(Base):
    """
    Shift Lead specific data - manages driver work hours within a city
    """
    __tablename__ = "shift_leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True)

    # Work hour constraints for drivers they manage
    min_hours_per_shift: Mapped[int] = mapped_column(default=4)
    max_hours_per_shift: Mapped[int] = mapped_column(default=12)
    min_hours_per_week: Mapped[int] = mapped_column(default=20)
    max_hours_per_week: Mapped[int] = mapped_column(default=60)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    city: Mapped["City"] = relationship("City", foreign_keys=[city_id])

    __table_args__ = (
        UniqueConstraint('user_id', 'city_id', name='uq_shift_lead_user_city'),
        Index('idx_shift_leads_city_active', 'city_id', 'is_active'),
    )

    def __repr__(self):
        return f"<ShiftLead user={self.user_id} city={self.city_id}>"

