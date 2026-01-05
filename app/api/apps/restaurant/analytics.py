"""Restaurant analytics and statistics"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_restaurant_owner
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.order import Order, OrderStatus

router = APIRouter()


class AnalyticsSummary(BaseModel):
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: float
    average_order_value: float


@router.get("/restaurant/{restaurant_id}", response_model=AnalyticsSummary)
async def get_restaurant_analytics(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get analytics for a restaurant"""
    # Verify ownership
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Total orders
    total_orders_result = await session.execute(
        select(func.count(Order.id))
        .where(Order.restaurant_id == restaurant_id)
    )
    total_orders = total_orders_result.scalar() or 0

    # Completed orders
    completed_orders_result = await session.execute(
        select(func.count(Order.id))
        .where(Order.restaurant_id == restaurant_id)
        .where(Order.status == OrderStatus.delivered)
    )
    completed_orders = completed_orders_result.scalar() or 0

    # Cancelled orders
    cancelled_orders_result = await session.execute(
        select(func.count(Order.id))
        .where(Order.restaurant_id == restaurant_id)
        .where(Order.status == OrderStatus.cancelled)
    )
    cancelled_orders = cancelled_orders_result.scalar() or 0

    # Total revenue
    revenue_result = await session.execute(
        select(func.sum(Order.total))
        .where(Order.restaurant_id == restaurant_id)
        .where(Order.status == OrderStatus.delivered)
    )
    total_revenue = float(revenue_result.scalar() or 0)

    # Average order value
    average_order_value = total_revenue / completed_orders if completed_orders > 0 else 0

    return AnalyticsSummary(
        total_orders=total_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value
    )

