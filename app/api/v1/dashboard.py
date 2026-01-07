"""
Admin Dashboard - Main dashboard with overview and statistics

This provides a centralized view for managing:
- User roles and permissions
- Cities and operations
- Restaurant approvals
- Orders and deliveries
- Shift leads and driver management
- System statistics
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.deps import get_session, get_current_user
from app.core.rbac_deps import require_admin_access, get_current_user_scopes
from app.models.user import User
from app.models.rbac import Role, UserRole as UserRoleModel, City, ShiftLead
from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant
from app.services.rbac_service import UserScopes

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])

# Templates directory will be created
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)]
):
    """
    Main dashboard page with overview statistics
    """
    # Get statistics based on user's scope
    stats = await get_dashboard_stats(session, scopes)

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "stats": stats,
            "page": "dashboard"
        }
    )


@router.get("/roles", response_class=HTMLResponse)
async def roles_management(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)]
):
    """
    Role management page - view and manage roles
    """
    # Get all roles
    result = await session.execute(
        select(Role).where(Role.is_active == True).order_by(Role.code)
    )
    roles = result.scalars().all()

    return templates.TemplateResponse(
        "dashboard/roles.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "roles": roles,
            "page": "roles"
        }
    )


@router.get("/user-roles", response_class=HTMLResponse)
async def user_roles_management(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)],
    user_id: Optional[int] = Query(None),
    city_id: Optional[int] = Query(None)
):
    """
    User role assignments page - assign/revoke roles
    """
    # Build query for user roles
    query = select(UserRoleModel, Role, User).join(
        Role, UserRoleModel.role_id == Role.id
    ).join(
        User, UserRoleModel.user_id == User.id
    ).where(UserRoleModel.is_active == True)

    # Apply scope filters
    if not scopes.is_super_admin:
        if scopes.has_city_scope():
            query = query.where(UserRoleModel.city_id.in_(scopes.city_ids))
        else:
            query = query.where(UserRoleModel.user_id == user.id)

    # Apply filters
    if user_id:
        query = query.where(UserRoleModel.user_id == user_id)
    if city_id:
        query = query.where(UserRoleModel.city_id == city_id)

    result = await session.execute(query.order_by(UserRoleModel.assigned_at.desc()))
    user_roles = result.all()

    # Get all users for assignment dropdown
    users_result = await session.execute(select(User).limit(100))
    all_users = users_result.scalars().all()

    # Get all roles for assignment dropdown
    roles_result = await session.execute(select(Role).where(Role.is_active == True))
    all_roles = roles_result.scalars().all()

    # Get cities for scope selection
    cities_result = await session.execute(select(City).where(City.is_active == True))
    all_cities = cities_result.scalars().all()

    return templates.TemplateResponse(
        "dashboard/user_roles.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "user_roles": user_roles,
            "all_users": all_users,
            "all_roles": all_roles,
            "all_cities": all_cities,
            "page": "user_roles"
        }
    )


@router.get("/cities", response_class=HTMLResponse)
async def cities_management(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)]
):
    """
    Cities management page
    """
    # Get cities based on scope
    query = select(City).where(City.is_active == True)

    if not scopes.is_super_admin and scopes.has_city_scope():
        query = query.where(City.id.in_(scopes.city_ids))

    result = await session.execute(query.order_by(City.name))
    cities = result.scalars().all()

    # Get city statistics
    city_stats = {}
    for city in cities:
        # Count restaurants
        rest_count = await session.execute(
            select(func.count()).select_from(Restaurant).where(
                Restaurant.city_id == city.id,
                Restaurant.is_active == True
            )
        )

        # Count orders
        order_count = await session.execute(
            select(func.count()).select_from(Order).where(
                Order.city_id == city.id
            )
        )

        city_stats[city.id] = {
            "restaurants": rest_count.scalar(),
            "orders": order_count.scalar()
        }

    return templates.TemplateResponse(
        "dashboard/cities.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "cities": cities,
            "city_stats": city_stats,
            "page": "cities"
        }
    )


@router.get("/restaurants", response_class=HTMLResponse)
async def restaurants_management(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)],
    city_id: Optional[int] = Query(None),
    pending_only: bool = Query(False)
):
    """
    Restaurant management page - approve/manage restaurants
    """
    # Build query
    query = select(Restaurant)

    # Apply scope filters
    if not scopes.is_super_admin:
        if scopes.has_city_scope():
            query = query.where(Restaurant.city_id.in_(scopes.city_ids))
        elif scopes.has_restaurant_scope():
            query = query.where(Restaurant.id.in_(scopes.restaurant_ids))

    # Apply filters
    if city_id:
        query = query.where(Restaurant.city_id == city_id)

    if pending_only:
        query = query.where(Restaurant.is_approved == False)

    result = await session.execute(query.order_by(Restaurant.created_at.desc()).limit(100))
    restaurants = result.scalars().all()

    # Get cities for filter
    cities_query = select(City).where(City.is_active == True)
    if not scopes.is_super_admin and scopes.has_city_scope():
        cities_query = cities_query.where(City.id.in_(scopes.city_ids))

    cities_result = await session.execute(cities_query)
    cities = cities_result.scalars().all()

    return templates.TemplateResponse(
        "dashboard/restaurants.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "restaurants": restaurants,
            "cities": cities,
            "page": "restaurants"
        }
    )


@router.get("/orders", response_class=HTMLResponse)
async def orders_management(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)],
    city_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Orders management page - view and manage orders
    """
    # Build query
    query = select(Order)

    # Apply scope filters
    if not scopes.is_super_admin:
        if scopes.has_city_scope():
            query = query.where(Order.city_id.in_(scopes.city_ids))
        elif scopes.has_restaurant_scope():
            query = query.where(Order.restaurant_id.in_(scopes.restaurant_ids))

    # Apply filters
    if city_id:
        query = query.where(Order.city_id == city_id)

    if status:
        query = query.where(Order.status == status)

    result = await session.execute(
        query.order_by(Order.created_at.desc()).limit(100)
    )
    orders = result.scalars().all()

    # Get cities for filter
    cities_query = select(City).where(City.is_active == True)
    if not scopes.is_super_admin and scopes.has_city_scope():
        cities_query = cities_query.where(City.id.in_(scopes.city_ids))

    cities_result = await session.execute(cities_query)
    cities = cities_result.scalars().all()

    return templates.TemplateResponse(
        "dashboard/orders.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "orders": orders,
            "cities": cities,
            "order_statuses": [s.value for s in OrderStatus],
            "page": "orders"
        }
    )


@router.get("/shift-leads", response_class=HTMLResponse)
async def shift_leads_management(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(require_admin_access)],
    city_id: Optional[int] = Query(None)
):
    """
    Shift leads management page
    """
    # Build query
    query = select(ShiftLead).where(ShiftLead.is_active == True)

    # Apply scope filters
    if not scopes.is_super_admin and scopes.has_city_scope():
        query = query.where(ShiftLead.city_id.in_(scopes.city_ids))

    # Apply filter
    if city_id:
        query = query.where(ShiftLead.city_id == city_id)

    result = await session.execute(query)
    shift_leads = result.scalars().all()

    # Get cities for filter and assignment
    cities_query = select(City).where(City.is_active == True)
    if not scopes.is_super_admin and scopes.has_city_scope():
        cities_query = cities_query.where(City.id.in_(scopes.city_ids))

    cities_result = await session.execute(cities_query)
    cities = cities_result.scalars().all()

    # Get users for assignment
    users_result = await session.execute(select(User).limit(100))
    users = users_result.scalars().all()

    return templates.TemplateResponse(
        "dashboard/shift_leads.html",
        {
            "request": request,
            "user": user,
            "scopes": scopes,
            "shift_leads": shift_leads,
            "cities": cities,
            "users": users,
            "page": "shift_leads"
        }
    )


async def get_dashboard_stats(session: AsyncSession, scopes: UserScopes):
    """
    Get dashboard statistics based on user's scope
    """
    stats = {
        "total_orders": 0,
        "pending_orders": 0,
        "completed_orders": 0,
        "total_revenue": 0.0,
        "active_restaurants": 0,
        "pending_approvals": 0,
        "total_cities": 0,
        "active_riders": 0,
        "recent_orders": []
    }

    # Base queries
    orders_query = select(Order)
    restaurants_query = select(Restaurant).where(Restaurant.is_active == True)

    # Apply scope filters
    if not scopes.is_super_admin:
        if scopes.has_city_scope():
            orders_query = orders_query.where(Order.city_id.in_(scopes.city_ids))
            restaurants_query = restaurants_query.where(Restaurant.city_id.in_(scopes.city_ids))
        elif scopes.has_restaurant_scope():
            orders_query = orders_query.where(Order.restaurant_id.in_(scopes.restaurant_ids))
            restaurants_query = restaurants_query.where(Restaurant.id.in_(scopes.restaurant_ids))

    # Total orders
    total_orders_result = await session.execute(
        select(func.count()).select_from(orders_query.subquery())
    )
    stats["total_orders"] = total_orders_result.scalar()

    # Pending orders
    pending_query = orders_query.where(Order.status.in_([
        OrderStatus.created, OrderStatus.confirmed, OrderStatus.preparing,
        OrderStatus.ready, OrderStatus.assigned, OrderStatus.picked_up
    ]))
    pending_result = await session.execute(
        select(func.count()).select_from(pending_query.subquery())
    )
    stats["pending_orders"] = pending_result.scalar()

    # Completed orders
    completed_query = orders_query.where(Order.status == OrderStatus.delivered)
    completed_result = await session.execute(
        select(func.count()).select_from(completed_query.subquery())
    )
    stats["completed_orders"] = completed_result.scalar()

    # Total revenue
    revenue_query = orders_query.where(Order.status == OrderStatus.delivered).with_only_columns(func.sum(Order.total))
    revenue_result = await session.execute(revenue_query)
    stats["total_revenue"] = float(revenue_result.scalar() or 0)

    # Active restaurants
    restaurants_result = await session.execute(
        select(func.count()).select_from(restaurants_query.subquery())
    )
    stats["active_restaurants"] = restaurants_result.scalar()

    # Pending approvals
    pending_approvals_query = restaurants_query.where(Restaurant.is_approved == False)
    pending_approvals_result = await session.execute(
        select(func.count()).select_from(pending_approvals_query.subquery())
    )
    stats["pending_approvals"] = pending_approvals_result.scalar()

    # Total cities (if applicable)
    if scopes.is_super_admin:
        cities_result = await session.execute(
            select(func.count()).select_from(City).where(City.is_active == True)
        )
        stats["total_cities"] = cities_result.scalar()
    else:
        stats["total_cities"] = len(scopes.city_ids)

    # Recent orders
    recent_orders_result = await session.execute(
        orders_query.order_by(Order.created_at.desc()).limit(10)
    )
    stats["recent_orders"] = recent_orders_result.scalars().all()

    return stats

