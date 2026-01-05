"""Rider/Driver shift management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_driver
from app.models.user import User
from app.models.driver import Driver, Shift

router = APIRouter()


class ShiftResponse(BaseModel):
    id: int
    driver_id: int
    start_time: datetime
    end_time: datetime | None
    start_lat: float | None
    start_lon: float | None
    end_lat: float | None
    end_lon: float | None

    class Config:
        from_attributes = True


@router.post("/start", status_code=201)
async def start_shift(
    lat: float | None = None,
    lon: float | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Start a new shift"""
    # Get driver
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    # Check if there's an active shift
    active_shift = await session.execute(
        select(Shift)
        .where(Shift.driver_id == driver.id)
        .where(Shift.end_time == None)
    )
    if active_shift.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Active shift already exists")

    shift = Shift(
        driver_id=driver.id,
        start_time=datetime.utcnow(),
        start_lat=lat,
        start_lon=lon
    )
    session.add(shift)
    driver.is_available = True
    await session.commit()

    return {"message": "Shift started", "shift_id": shift.id}


@router.post("/end")
async def end_shift(
    lat: float | None = None,
    lon: float | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """End the current shift"""
    # Get driver
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    # Find active shift
    active_shift_result = await session.execute(
        select(Shift)
        .where(Shift.driver_id == driver.id)
        .where(Shift.end_time == None)
    )
    shift = active_shift_result.scalar_one_or_none()

    if not shift:
        raise HTTPException(status_code=404, detail="No active shift found")

    shift.end_time = datetime.utcnow()
    shift.end_lat = lat
    shift.end_lon = lon
    driver.is_available = False
    await session.commit()

    return {"message": "Shift ended", "shift_id": shift.id}


@router.get("/active", response_model=ShiftResponse | None)
async def get_active_shift(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Get current active shift"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    shift_result = await session.execute(
        select(Shift)
        .where(Shift.driver_id == driver.id)
        .where(Shift.end_time == None)
    )
    shift = shift_result.scalar_one_or_none()

    if not shift:
        return None

    return ShiftResponse.model_validate(shift)


@router.get("/history", response_model=list[ShiftResponse])
async def get_shift_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver),
    limit: int = 20
):
    """Get shift history"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    shifts_result = await session.execute(
        select(Shift)
        .where(Shift.driver_id == driver.id)
        .order_by(Shift.start_time.desc())
        .limit(limit)
    )
    shifts = shifts_result.scalars().all()

    return [ShiftResponse.model_validate(s) for s in shifts]

