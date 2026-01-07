"""
RBAC Dependencies - FastAPI dependencies for role-based access control

These dependencies are used in route handlers to enforce permissions:
- require_roles: Ensure user has one of the required roles
- require_super_admin: Super admin only
- require_city_access: City admin, dispatcher, support, shift lead
- require_restaurant_admin: Restaurant admin only
- And more...
"""
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session
from app.models.user import User
from app.models.rbac import RoleCode
from app.services.rbac_service import (
    get_user_scopes,
    check_role_permission,
    UserScopes
)


async def get_current_user_scopes(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """
    Get the current user's RBAC scopes

    This dependency is used to check what permissions the user has
    """
    return await get_user_scopes(session, user.id)


def require_roles(*role_codes: str):
    """
    Dependency factory to require one or more roles

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: User = Depends(get_current_user),
            scopes: UserScopes = Depends(require_roles("super_admin", "city_admin"))
        ):
            # User must be super_admin OR city_admin
            ...

    Args:
        *role_codes: One or more role code strings

    Returns:
        FastAPI dependency function
    """
    async def check_roles(
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_session)]
    ) -> UserScopes:
        scopes = await get_user_scopes(session, user.id)

        # Super admin bypasses all checks
        if scopes.is_super_admin:
            return scopes

        # Check if user has any of the required roles
        if not scopes.has_role(*role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role(s): {', '.join(role_codes)}"
            )

        return scopes

    return check_roles


def require_city_access(city_id: Optional[int] = None):
    """
    Dependency factory to require access to a specific city

    Usage:
        @router.get("/cities/{city_id}/orders")
        async def get_city_orders(
            city_id: int,
            scopes: UserScopes = Depends(require_city_access())
        ):
            # Will be validated automatically
            if not scopes.can_access_city(city_id):
                raise HTTPException(403)
            ...

    Args:
        city_id: Optional city ID to check (if None, just check city-level access)

    Returns:
        FastAPI dependency function
    """
    async def check_city_access(
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_session)]
    ) -> UserScopes:
        scopes = await get_user_scopes(session, user.id)

        # Super admin bypasses checks
        if scopes.is_super_admin:
            return scopes

        # Check if user has city-level access
        if not scopes.has_city_scope():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="City-level access required"
            )

        # If specific city_id provided, verify access
        if city_id is not None and not scopes.can_access_city(city_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to city {city_id}"
            )

        return scopes

    return check_city_access


def require_restaurant_access(restaurant_id: Optional[int] = None):
    """
    Dependency factory to require access to a specific restaurant

    Usage:
        @router.patch("/restaurants/{restaurant_id}")
        async def update_restaurant(
            restaurant_id: int,
            scopes: UserScopes = Depends(require_restaurant_access())
        ):
            if not scopes.can_access_restaurant(restaurant_id):
                raise HTTPException(403)
            ...
    """
    async def check_restaurant_access(
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_session)]
    ) -> UserScopes:
        scopes = await get_user_scopes(session, user.id)

        # Super admin bypasses checks
        if scopes.is_super_admin:
            return scopes

        # Check if user has restaurant-level access
        if not scopes.has_restaurant_scope():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Restaurant-level access required"
            )

        # If specific restaurant_id provided, verify access
        if restaurant_id is not None and not scopes.can_access_restaurant(restaurant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to restaurant {restaurant_id}"
            )

        return scopes

    return check_restaurant_access


# Predefined role dependencies for common use cases

async def require_super_admin(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """Require super admin role"""
    scopes = await get_user_scopes(session, user.id)

    if not scopes.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    return scopes


async def require_city_admin(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """Require city admin role"""
    return await require_roles(RoleCode.CITY_ADMIN, RoleCode.SUPER_ADMIN)(user, session)


async def require_shift_lead(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """Require shift lead role"""
    return await require_roles(RoleCode.SHIFT_LEAD, RoleCode.CITY_ADMIN, RoleCode.SUPER_ADMIN)(user, session)


async def require_dispatcher(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """Require dispatcher role"""
    return await require_roles(RoleCode.DISPATCHER, RoleCode.CITY_ADMIN, RoleCode.SUPER_ADMIN)(user, session)


async def require_support(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """Require support role"""
    return await require_roles(RoleCode.SUPPORT, RoleCode.CITY_ADMIN, RoleCode.SUPER_ADMIN)(user, session)


async def require_restaurant_admin_role(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """Require restaurant admin role"""
    return await require_roles(RoleCode.RESTAURANT_ADMIN, RoleCode.SUPER_ADMIN)(user, session)


async def require_admin_access(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> UserScopes:
    """
    Require any admin-level access (super admin, city admin, or restaurant admin)
    """
    return await require_roles(
        RoleCode.SUPER_ADMIN,
        RoleCode.CITY_ADMIN,
        RoleCode.RESTAURANT_ADMIN
    )(user, session)


class ScopeValidator:
    """
    Helper class to validate scope access within route handlers

    Usage:
        @router.get("/orders/{order_id}")
        async def get_order(
            order_id: int,
            scopes: UserScopes = Depends(require_admin_access),
            session: AsyncSession = Depends(get_session)
        ):
            order = await session.get(Order, order_id)
            ScopeValidator.ensure_city_access(scopes, order.city_id)
            return order
    """

    @staticmethod
    def ensure_city_access(scopes: UserScopes, city_id: int):
        """Raise 403 if user cannot access the city"""
        if not scopes.can_access_city(city_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to city {city_id}"
            )

    @staticmethod
    def ensure_restaurant_access(scopes: UserScopes, restaurant_id: int):
        """Raise 403 if user cannot access the restaurant"""
        if not scopes.can_access_restaurant(restaurant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to restaurant {restaurant_id}"
            )

    @staticmethod
    def ensure_user_access(scopes: UserScopes, user_id: int):
        """Raise 403 if user cannot access another user's data"""
        if not scopes.can_access_user(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other user's data"
            )

    @staticmethod
    def ensure_order_access(scopes: UserScopes, order):
        """
        Raise 403 if user cannot access the order

        Args:
            scopes: User's scopes
            order: Order model instance with city_id, restaurant_id, customer_id
        """
        if scopes.is_super_admin:
            return

        # City admin can access orders in their cities
        if scopes.has_city_scope() and scopes.can_access_city(order.city_id):
            return

        # Restaurant admin can access orders for their restaurants
        if scopes.has_restaurant_scope() and scopes.can_access_restaurant(order.restaurant_id):
            return

        # Customer can access their own orders
        if scopes.is_self_only and order.customer_id == scopes.user_id:
            return

        # Rider can access orders assigned to them
        if scopes.is_self_only and order.rider_id == scopes.user_id:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this order"
        )

