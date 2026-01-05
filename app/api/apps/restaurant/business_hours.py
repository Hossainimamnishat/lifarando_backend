"""Restaurant business hours management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_restaurant_owner
from app.models.user import User
from app.models.restaurant import Restaurant, BusinessHour

router = APIRouter()


class BusinessHourResponse(BaseModel):
    id: int
    restaurant_id: int
    day_of_week: int
    open_time: time
    close_time: time
    is_closed: bool

    class Config:
        from_attributes = True


class BusinessHourRequest(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    open_time: time
    close_time: time
    is_closed: bool = False


@router.get("/restaurant/{restaurant_id}", response_model=list[BusinessHourResponse])
async def get_business_hours(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get business hours for a restaurant"""
    # Verify ownership
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    result = await session.execute(
        select(BusinessHour)
        .where(BusinessHour.restaurant_id == restaurant_id)
        .order_by(BusinessHour.day_of_week)
    )
    hours = result.scalars().all()

    return [BusinessHourResponse.model_validate(h) for h in hours]


@router.post("/restaurant/{restaurant_id}", response_model=BusinessHourResponse, status_code=201)
async def create_business_hour(
    restaurant_id: int,
    data: BusinessHourRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Create business hours for a specific day"""
    # Verify ownership
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if hours already exist for this day
    existing = await session.execute(
        select(BusinessHour)
        .where(BusinessHour.restaurant_id == restaurant_id)
        .where(BusinessHour.day_of_week == data.day_of_week)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Business hours already exist for this day")

    business_hour = BusinessHour(
        restaurant_id=restaurant_id,
        day_of_week=data.day_of_week,
        open_time=data.open_time,
        close_time=data.close_time,
        is_closed=data.is_closed
    )
    session.add(business_hour)
    await session.commit()
    await session.refresh(business_hour)

    return BusinessHourResponse.model_validate(business_hour)


@router.patch("/{hour_id}", response_model=BusinessHourResponse)
async def update_business_hour(
    hour_id: int,
    data: BusinessHourRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Update business hours"""
    hour = await session.get(BusinessHour, hour_id)
    if not hour:
        raise HTTPException(status_code=404, detail="Business hour not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, hour.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    hour.day_of_week = data.day_of_week
    hour.open_time = data.open_time
    hour.close_time = data.close_time
    hour.is_closed = data.is_closed

    await session.commit()
    await session.refresh(hour)

    return BusinessHourResponse.model_validate(hour)


@router.delete("/{hour_id}", status_code=204)
async def delete_business_hour(
    hour_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Delete business hours"""
    hour = await session.get(BusinessHour, hour_id)
    if not hour:
        raise HTTPException(status_code=404, detail="Business hour not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, hour.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await session.delete(hour)
    await session.commit()

    return None

