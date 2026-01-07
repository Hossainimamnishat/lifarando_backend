"""
RBAC Service - Role-Based Access Control Business Logic

This module provides the core RBAC functionality:
- Fetching user scopes from database
- Checking permissions
- Applying scope filters to queries
"""
from typing import Optional
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from app.models.rbac import UserRole, Role, ScopeType, RoleCode


@dataclass
class UserScopes:
    """
    Represents a user's access scopes across the system
    """
    user_id: int
    is_super_admin: bool = False
    city_ids: set[int] = None
    restaurant_ids: set[int] = None
    is_self_only: bool = False
    role_codes: set[str] = None

    def __post_init__(self):
        if self.city_ids is None:
            self.city_ids = set()
        if self.restaurant_ids is None:
            self.restaurant_ids = set()
        if self.role_codes is None:
            self.role_codes = set()

    def has_role(self, *role_codes: str) -> bool:
        """Check if user has any of the specified roles"""
        return bool(self.role_codes & set(role_codes))

    def can_access_city(self, city_id: int) -> bool:
        """Check if user can access a specific city"""
        return self.is_super_admin or city_id in self.city_ids

    def can_access_restaurant(self, restaurant_id: int) -> bool:
        """Check if user can access a specific restaurant"""
        return self.is_super_admin or restaurant_id in self.restaurant_ids

    def can_access_user(self, target_user_id: int) -> bool:
        """Check if user can access another user's data"""
        return self.is_super_admin or (self.is_self_only and target_user_id == self.user_id)

    def has_city_scope(self) -> bool:
        """Check if user has any city-level access"""
        return self.is_super_admin or len(self.city_ids) > 0

    def has_restaurant_scope(self) -> bool:
        """Check if user has any restaurant-level access"""
        return self.is_super_admin or len(self.restaurant_ids) > 0


async def get_user_scopes(session: AsyncSession, user_id: int) -> UserScopes:
    """
    Fetch all active scopes for a user from the database

    Returns:
        UserScopes object containing all permissions and scope information
    """
    # Query all active user roles with their role definitions
    result = await session.execute(
        select(UserRole, Role)
        .join(Role, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .where(UserRole.is_active == True)
        .where(Role.is_active == True)
    )

    user_roles = result.all()

    scopes = UserScopes(user_id=user_id)

    for user_role, role in user_roles:
        scopes.role_codes.add(role.code)

        # Check for super admin
        if role.code == RoleCode.SUPER_ADMIN:
            scopes.is_super_admin = True
            continue

        # Handle city-scoped roles
        if role.scope_type == ScopeType.CITY and user_role.city_id:
            scopes.city_ids.add(user_role.city_id)

        # Handle restaurant-scoped roles
        if role.scope_type == ScopeType.RESTAURANT and user_role.restaurant_id:
            scopes.restaurant_ids.add(user_role.restaurant_id)

        # Handle self-scoped roles
        if role.scope_type == ScopeType.SELF:
            scopes.is_self_only = True

    return scopes


def apply_scope_filters(query, model, scopes: UserScopes, user_id_field: str = None):
    """
    Apply scope-based filters to a SQLAlchemy query

    Args:
        query: SQLAlchemy query object
        model: The model being queried (Order, Restaurant, etc.)
        scopes: UserScopes object with permission information
        user_id_field: Name of the user_id field for SELF scope (e.g., 'customer_id', 'rider_id')

    Returns:
        Filtered query object

    Usage:
        query = select(Order)
        query = apply_scope_filters(query, Order, scopes, user_id_field='customer_id')
        result = await session.execute(query)
    """
    # Super admin bypasses all filters
    if scopes.is_super_admin:
        return query

    # Apply city filter if model has city_id and user has city scope
    if hasattr(model, 'city_id') and scopes.city_ids:
        query = query.where(model.city_id.in_(scopes.city_ids))

    # Apply restaurant filter if model has restaurant_id and user has restaurant scope
    if hasattr(model, 'restaurant_id') and scopes.restaurant_ids:
        query = query.where(model.restaurant_id.in_(scopes.restaurant_ids))

    # Apply self filter if specified and user is self-only
    if user_id_field and scopes.is_self_only:
        query = query.where(getattr(model, user_id_field) == scopes.user_id)

    return query


async def check_role_permission(
    session: AsyncSession,
    user_id: int,
    required_roles: list[str],
    city_id: Optional[int] = None,
    restaurant_id: Optional[int] = None
) -> bool:
    """
    Check if user has any of the required roles with optional scope verification

    Args:
        session: Database session
        user_id: User to check
        required_roles: List of role codes (e.g., ['city_admin', 'dispatcher'])
        city_id: If provided, verify user has role for this specific city
        restaurant_id: If provided, verify user has role for this specific restaurant

    Returns:
        True if user has permission, False otherwise
    """
    scopes = await get_user_scopes(session, user_id)

    # Super admin always has permission
    if scopes.is_super_admin:
        return True

    # Check if user has any of the required roles
    if not scopes.has_role(*required_roles):
        return False

    # Verify city scope if required
    if city_id is not None and not scopes.can_access_city(city_id):
        return False

    # Verify restaurant scope if required
    if restaurant_id is not None and not scopes.can_access_restaurant(restaurant_id):
        return False

    return True


async def can_assign_role(
    session: AsyncSession,
    assigner_user_id: int,
    role_code: str,
    target_city_id: Optional[int] = None,
    target_restaurant_id: Optional[int] = None
) -> bool:
    """
    Check if a user can assign a specific role to another user

    Rules:
    - Super Admin can assign any role
    - City Admin can assign city-scoped roles only within their cities
    - Restaurant Admin cannot assign roles
    - Others cannot assign roles

    Args:
        session: Database session
        assigner_user_id: User attempting to assign the role
        role_code: Role being assigned
        target_city_id: City scope of the assignment (if city-scoped)
        target_restaurant_id: Restaurant scope of the assignment (if restaurant-scoped)

    Returns:
        True if assignment is allowed, False otherwise
    """
    assigner_scopes = await get_user_scopes(session, assigner_user_id)

    # Super admin can assign anything
    if assigner_scopes.is_super_admin:
        return True

    # City Admin can assign city-scoped roles within their cities
    if assigner_scopes.has_role(RoleCode.CITY_ADMIN):
        # Get the role being assigned
        result = await session.execute(
            select(Role).where(Role.code == role_code)
        )
        role = result.scalar_one_or_none()

        if not role:
            return False

        # Can only assign city-scoped roles
        if role.scope_type != ScopeType.CITY:
            return False

        # Can only assign within their own cities
        if target_city_id and assigner_scopes.can_access_city(target_city_id):
            return True

    return False


async def get_accessible_cities(session: AsyncSession, user_id: int) -> list[int]:
    """Get list of city IDs the user can access"""
    scopes = await get_user_scopes(session, user_id)

    if scopes.is_super_admin:
        # Return all active cities
        result = await session.execute(
            select(City.id).where(City.is_active == True)
        )
        return [row[0] for row in result.all()]

    return list(scopes.city_ids)


async def get_accessible_restaurants(session: AsyncSession, user_id: int) -> list[int]:
    """Get list of restaurant IDs the user can access"""
    scopes = await get_user_scopes(session, user_id)

    if scopes.is_super_admin:
        # Return all active restaurants
        from app.models.restaurant import Restaurant
        result = await session.execute(
            select(Restaurant.id).where(Restaurant.is_active == True)
        )
        return [row[0] for row in result.all()]

    if scopes.has_city_scope():
        # Return all restaurants in accessible cities
        from app.models.restaurant import Restaurant
        result = await session.execute(
            select(Restaurant.id)
            .where(Restaurant.city_id.in_(scopes.city_ids))
            .where(Restaurant.is_active == True)
        )
        return [row[0] for row in result.all()]

    return list(scopes.restaurant_ids)


# Import City here to avoid circular imports
from app.models.rbac import City

