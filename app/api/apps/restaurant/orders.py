"""Restaurant order management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_restaurant_owner
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.order import Order, OrderStatus

router = APIRouter()


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    customer_address: str | None
    order_type: str
    status: str
    subtotal: float
    total: float
    created_at: str

    class Config:
        from_attributes = True


@router.get("/restaurant/{restaurant_id}", response_model=list[OrderResponse])
async def get_restaurant_orders(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner),
    status: OrderStatus | None = None
):
    """Get all orders for a restaurant"""
    # Verify ownership
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    query = select(Order).where(Order.restaurant_id == restaurant_id)

    if status:
        query = query.where(Order.status == status)

    query = query.order_by(Order.created_at.desc())

    result = await session.execute(query)
    orders = result.scalars().all()

    return [
        OrderResponse(
            id=o.id,
            customer_name=o.customer_name,
            customer_phone=o.customer_phone,
            customer_address=o.customer_address,
            order_type=o.order_type.value,
            status=o.status.value,
            subtotal=float(o.subtotal),
            total=float(o.total),
            created_at=o.created_at.isoformat()
        )
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get order details"""
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, order.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=order.id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_address=order.customer_address,
        order_type=order.order_type.value,
        status=order.status.value,
        subtotal=float(order.subtotal),
        total=float(order.total),
        created_at=order.created_at.isoformat()
    )


@router.post("/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Confirm an order"""
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, order.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status != OrderStatus.created:
        raise HTTPException(status_code=400, detail="Order cannot be confirmed")

    order.status = OrderStatus.confirmed
    await session.commit()

    return {"message": "Order confirmed", "order_id": order.id}


@router.post("/{order_id}/preparing")
async def mark_preparing(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Mark order as being prepared"""
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, order.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status != OrderStatus.confirmed:
        raise HTTPException(status_code=400, detail="Order must be confirmed first")

    order.status = OrderStatus.preparing
    await session.commit()

    return {"message": "Order is being prepared", "order_id": order.id}


@router.post("/{order_id}/ready")
async def mark_ready(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Mark order as ready for pickup/delivery"""
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, order.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status != OrderStatus.preparing:
        raise HTTPException(status_code=400, detail="Order must be preparing first")

    order.status = OrderStatus.ready
    await session.commit()

    return {"message": "Order is ready", "order_id": order.id}


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Cancel an order"""
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, order.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status in [OrderStatus.delivered, OrderStatus.cancelled]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")

    order.status = OrderStatus.cancelled
    await session.commit()

    return {"message": "Order cancelled", "order_id": order.id}

