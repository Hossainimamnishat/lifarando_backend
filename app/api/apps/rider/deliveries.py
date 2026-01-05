"""Rider/Driver delivery management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_driver
from app.models.user import User
from app.models.driver import Driver, Delivery
from app.models.order import Order, OrderStatus

router = APIRouter()


class DeliveryResponse(BaseModel):
    id: int
    order_id: int
    driver_id: int
    status: str
    pickup_time: datetime | None
    delivery_time: datetime | None
    driver_earning: float | None

    class Config:
        from_attributes = True


class OrderDetailsResponse(BaseModel):
    order_id: int
    restaurant_name: str
    customer_name: str
    customer_phone: str
    customer_address: str | None
    customer_lat: float | None
    customer_lon: float | None
    delivery_note: str | None
    total: float


@router.get("/available", response_model=list[dict])
async def get_available_deliveries(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Get available deliveries waiting for assignment"""
    # Find orders that are ready and not assigned
    result = await session.execute(
        select(Order)
        .where(Order.status == OrderStatus.ready)
        .where(~Order.id.in_(
            select(Delivery.order_id).where(Delivery.pickup_time != None)
        ))
        .limit(20)
    )
    orders = result.scalars().all()

    return [
        {
            "order_id": o.id,
            "restaurant_id": o.restaurant_id,
            "customer_address": o.customer_address,
            "distance_km": o.distance_km,
            "total": float(o.total)
        }
        for o in orders
    ]


@router.post("/accept/{order_id}", status_code=201)
async def accept_delivery(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Accept a delivery assignment"""
    # Get driver
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver or not driver.is_available:
        raise HTTPException(status_code=400, detail="Driver not available")

    # Get order
    order = await session.get(Order, order_id)
    if not order or order.status != OrderStatus.ready:
        raise HTTPException(status_code=400, detail="Order not available for pickup")

    # Create delivery
    delivery = Delivery(
        order_id=order_id,
        driver_id=driver.id
    )
    session.add(delivery)
    order.status = OrderStatus.assigned
    await session.commit()

    return {"message": "Delivery accepted", "delivery_id": delivery.id}


@router.post("/{delivery_id}/pickup")
async def mark_picked_up(
    delivery_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Mark delivery as picked up from restaurant"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    delivery = await session.get(Delivery, delivery_id)
    if not delivery or delivery.driver_id != driver.id:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery.pickup_time:
        raise HTTPException(status_code=400, detail="Already marked as picked up")

    delivery.pickup_time = datetime.utcnow()

    # Update order status
    order = await session.get(Order, delivery.order_id)
    if order:
        order.status = OrderStatus.picked_up

    await session.commit()

    return {"message": "Marked as picked up"}


@router.post("/{delivery_id}/deliver")
async def mark_delivered(
    delivery_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Mark delivery as completed"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    delivery = await session.get(Delivery, delivery_id)
    if not delivery or delivery.driver_id != driver.id:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if not delivery.pickup_time:
        raise HTTPException(status_code=400, detail="Must mark as picked up first")

    if delivery.delivery_time:
        raise HTTPException(status_code=400, detail="Already marked as delivered")

    delivery.delivery_time = datetime.utcnow()

    # Update order status
    order = await session.get(Order, delivery.order_id)
    if order:
        order.status = OrderStatus.delivered
        # Calculate driver earning
        from app.config import settings
        if order.distance_km:
            delivery.driver_earning = order.distance_km * settings.BIKE_PAY_PER_KM

    await session.commit()

    return {"message": "Delivery completed", "earning": delivery.driver_earning}


@router.get("/active", response_model=list[DeliveryResponse])
async def get_active_deliveries(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Get current active deliveries for this driver"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    deliveries_result = await session.execute(
        select(Delivery)
        .where(Delivery.driver_id == driver.id)
        .where(Delivery.delivery_time == None)
    )
    deliveries = deliveries_result.scalars().all()

    return [DeliveryResponse.model_validate(d) for d in deliveries]


@router.get("/history", response_model=list[DeliveryResponse])
async def get_delivery_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver),
    limit: int = 50
):
    """Get delivery history"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    deliveries_result = await session.execute(
        select(Delivery)
        .where(Delivery.driver_id == driver.id)
        .where(Delivery.delivery_time != None)
        .order_by(Delivery.delivery_time.desc())
        .limit(limit)
    )
    deliveries = deliveries_result.scalars().all()

    return [DeliveryResponse.model_validate(d) for d in deliveries]

