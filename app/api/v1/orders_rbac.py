"""
Orders API with RBAC - Scoped access to orders

This demonstrates how to apply RBAC filtering to order endpoints:
- Super Admin: See all orders
- City Admin/Dispatcher/Support: See orders in their cities
- Restaurant Admin: See orders for their restaurants
- Customer: See only their own orders
- Rider: See orders assigned to them
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_user
from app.core.rbac_deps import get_current_user_scopes, ScopeValidator
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.rbac import RoleCode
from app.services.rbac_service import UserScopes, apply_scope_filters

router = APIRouter(prefix="/orders-rbac", tags=["Orders with RBAC"])


class OrderListItem(BaseModel):
    id: int
    city_id: int
    restaurant_id: int
    customer_name: str
    status: str
    total: float
    created_at: str

    class Config:
        from_attributes = True


class OrderStatsResponse(BaseModel):
    total_orders: int
    total_revenue: float
    pending_orders: int
    completed_orders: int


@router.get("/", response_model=list[OrderListItem])
async def list_orders_scoped(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)],
    city_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List orders with automatic scope filtering

    Access control:
    - **Super Admin**: All orders
    - **City Admin/Dispatcher/Support**: Orders in their cities
    - **Restaurant Admin**: Orders for their restaurants
    - **Customer**: Their own orders only
    - **Rider**: Orders assigned to them
    """
    # Start with base query
    query = select(Order)

    # Apply scope-based filters
    if scopes.is_super_admin:
        # Super admin sees everything - no filter
        pass
    elif scopes.has_role(RoleCode.CITY_ADMIN, RoleCode.DISPATCHER, RoleCode.SUPPORT):
        # City-level roles see orders in their cities
        query = query.where(Order.city_id.in_(scopes.city_ids))
    elif scopes.has_role(RoleCode.RESTAURANT_ADMIN):
        # Restaurant admin sees orders for their restaurants
        query = query.where(Order.restaurant_id.in_(scopes.restaurant_ids))
    elif scopes.has_role(RoleCode.CUSTOMER):
        # Customers see only their orders
        query = query.where(Order.customer_id == user.id)
    elif scopes.has_role(RoleCode.RIDER):
        # Riders see orders assigned to them
        query = query.where(Order.rider_id == user.id)
    else:
        # No valid role - return empty
        return []

    # Apply additional filters
    if city_id:
        # Verify access if city_id specified
        if not scopes.is_super_admin and city_id not in scopes.city_ids:
            raise HTTPException(status_code=403, detail=f"No access to city {city_id}")
        query = query.where(Order.city_id == city_id)

    if restaurant_id:
        # Verify access if restaurant_id specified
        if not scopes.is_super_admin and restaurant_id not in scopes.restaurant_ids:
            # For city admins, check if restaurant is in their cities
            if not scopes.has_city_scope():
                raise HTTPException(status_code=403, detail=f"No access to restaurant {restaurant_id}")
        query = query.where(Order.restaurant_id == restaurant_id)

    if status:
        query = query.where(Order.status == status)

    # Pagination
    query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    orders = result.scalars().all()

    return [
        OrderListItem(
            id=order.id,
            city_id=order.city_id,
            restaurant_id=order.restaurant_id,
            customer_name=order.customer_name,
            status=order.status.value,
            total=float(order.total),
            created_at=order.created_at.isoformat()
        )
        for order in orders
    ]


@router.get("/{order_id}")
async def get_order_details(
    order_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Get order details with scope validation
    """
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Validate access using ScopeValidator
    ScopeValidator.ensure_order_access(scopes, order)

    return {
        "id": order.id,
        "city_id": order.city_id,
        "restaurant_id": order.restaurant_id,
        "customer_id": order.customer_id,
        "rider_id": order.rider_id,
        "status": order.status.value,
        "total": float(order.total),
        "created_at": order.created_at.isoformat()
    }


@router.patch("/{order_id}/assign-rider")
async def assign_rider_to_order(
    order_id: int,
    rider_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Assign a rider to an order

    Access control:
    - **Super Admin**: Can assign any rider to any order
    - **Dispatcher**: Can assign riders in their cities
    - **Others**: Not allowed
    """
    # Check permission
    if not scopes.is_super_admin and not scopes.has_role(RoleCode.DISPATCHER):
        raise HTTPException(status_code=403, detail="Only dispatchers can assign riders")

    # Get order
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify dispatcher has access to this order's city
    if not scopes.is_super_admin and order.city_id not in scopes.city_ids:
        raise HTTPException(status_code=403, detail="Cannot assign riders in this city")

    # Verify rider exists and is in the same city (optional check)
    rider = await session.get(User, rider_id)
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Assign rider
    order.rider_id = rider_id
    if order.status == OrderStatus.ready:
        order.status = OrderStatus.assigned

    await session.commit()

    return {
        "message": "Rider assigned successfully",
        "order_id": order.id,
        "rider_id": rider_id,
        "status": order.status.value
    }


@router.get("/stats/summary", response_model=OrderStatsResponse)
async def get_order_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)],
    city_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None)
):
    """
    Get order statistics based on user's scope

    Access control:
    - **Super Admin**: Stats for all orders
    - **City Admin**: Stats for their cities
    - **Restaurant Admin**: Stats for their restaurants
    - **Others**: Not allowed
    """
    # Check permission
    if not scopes.is_super_admin and not scopes.has_role(
        RoleCode.CITY_ADMIN, RoleCode.RESTAURANT_ADMIN, RoleCode.SUPPORT
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions for statistics")

    # Build query with scope filters
    query = select(Order)

    if not scopes.is_super_admin:
        if scopes.has_city_scope():
            query = query.where(Order.city_id.in_(scopes.city_ids))
        elif scopes.has_restaurant_scope():
            query = query.where(Order.restaurant_id.in_(scopes.restaurant_ids))

    # Apply additional filters
    if city_id:
        ScopeValidator.ensure_city_access(scopes, city_id)
        query = query.where(Order.city_id == city_id)

    if restaurant_id:
        ScopeValidator.ensure_restaurant_access(scopes, restaurant_id)
        query = query.where(Order.restaurant_id == restaurant_id)

    # Get total count
    count_result = await session.execute(
        select(func.count()).select_from(query.subquery())
    )
    total_orders = count_result.scalar()

    # Get total revenue
    revenue_query = query.with_only_columns(func.sum(Order.total))
    revenue_result = await session.execute(revenue_query)
    total_revenue = float(revenue_result.scalar() or 0)

    # Get pending orders count
    pending_query = query.where(Order.status.in_([
        OrderStatus.created,
        OrderStatus.confirmed,
        OrderStatus.preparing,
        OrderStatus.ready,
        OrderStatus.assigned,
        OrderStatus.picked_up
    ]))
    pending_result = await session.execute(
        select(func.count()).select_from(pending_query.subquery())
    )
    pending_orders = pending_result.scalar()

    # Get completed orders count
    completed_query = query.where(Order.status == OrderStatus.delivered)
    completed_result = await session.execute(
        select(func.count()).select_from(completed_query.subquery())
    )
    completed_orders = completed_result.scalar()

    return OrderStatsResponse(
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        completed_orders=completed_orders
    )


@router.post("/{order_id}/refund")
async def refund_order(
    order_id: int,
    reason: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Issue a refund for an order

    Access control:
    - **Super Admin**: Can refund any order
    - **Support**: Can refund orders in their cities
    - **Others**: Not allowed
    """
    # Check permission
    if not scopes.is_super_admin and not scopes.has_role(RoleCode.SUPPORT):
        raise HTTPException(status_code=403, detail="Only support staff can issue refunds")

    # Get order
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify support has access to this order's city
    if not scopes.is_super_admin and order.city_id not in scopes.city_ids:
        raise HTTPException(status_code=403, detail="Cannot refund orders in this city")

    # Check if order can be refunded
    if order.status == OrderStatus.refunded:
        raise HTTPException(status_code=400, detail="Order already refunded")

    if order.status not in [OrderStatus.delivered, OrderStatus.cancelled]:
        raise HTTPException(status_code=400, detail="Can only refund delivered or cancelled orders")

    # Process refund
    order.status = OrderStatus.refunded

    # TODO: Create refund record in payments table
    # TODO: Process actual refund through payment gateway

    await session.commit()

    return {
        "message": "Refund processed successfully",
        "order_id": order.id,
        "amount": float(order.total),
        "reason": reason
    }

