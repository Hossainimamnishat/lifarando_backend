"""Rider/Driver earnings and statistics"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_driver
from app.models.user import User
from app.models.driver import Driver, Delivery

router = APIRouter()


class EarningsSummary(BaseModel):
    total_deliveries: int
    total_earnings: float
    average_per_delivery: float


@router.get("/summary", response_model=EarningsSummary)
async def get_earnings_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Get earnings summary for the driver"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    # Get completed deliveries
    stats_result = await session.execute(
        select(
            func.count(Delivery.id).label('total_deliveries'),
            func.sum(Delivery.driver_earning).label('total_earnings')
        )
        .where(Delivery.driver_id == driver.id)
        .where(Delivery.delivery_time != None)
    )
    stats = stats_result.first()

    total_deliveries = stats.total_deliveries or 0
    total_earnings = float(stats.total_earnings or 0)
    average_per_delivery = total_earnings / total_deliveries if total_deliveries > 0 else 0

    return EarningsSummary(
        total_deliveries=total_deliveries,
        total_earnings=total_earnings,
        average_per_delivery=average_per_delivery
    )

