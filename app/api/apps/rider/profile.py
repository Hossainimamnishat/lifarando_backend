"""Rider/Driver profile and vehicle management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_driver
from app.models.user import User
from app.models.driver import Driver, VehicleType

router = APIRouter()


class DriverProfileResponse(BaseModel):
    user_id: int
    email: str | None
    phone: str | None
    first_name: str
    last_name: str
    driver_id: int | None
    vehicle_type: str | None
    license_plate: str | None
    is_available: bool


class DriverProfileUpdateRequest(BaseModel):
    vehicle_type: VehicleType | None = None
    license_plate: str | None = None


@router.get("/", response_model=DriverProfileResponse)
async def get_driver_profile(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Get driver profile including vehicle info"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    return DriverProfileResponse(
        user_id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        driver_id=driver.id if driver else None,
        vehicle_type=driver.vehicle_type.value if driver and driver.vehicle_type else None,
        license_plate=driver.license_plate if driver else None,
        is_available=driver.is_available if driver else False
    )


@router.post("/", status_code=201)
async def create_driver_profile(
    data: DriverProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Create driver profile with vehicle information"""
    # Check if profile already exists
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Driver profile already exists")

    driver = Driver(
        user_id=user.id,
        vehicle_type=data.vehicle_type,
        license_plate=data.license_plate,
        is_available=False
    )
    session.add(driver)
    await session.commit()

    return {"message": "Driver profile created", "driver_id": driver.id}


@router.patch("/", response_model=DriverProfileResponse)
async def update_driver_profile(
    data: DriverProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Update driver profile"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    if data.vehicle_type is not None:
        driver.vehicle_type = data.vehicle_type
    if data.license_plate is not None:
        driver.license_plate = data.license_plate

    await session.commit()
    await session.refresh(driver)

    return DriverProfileResponse(
        user_id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        driver_id=driver.id,
        vehicle_type=driver.vehicle_type.value if driver.vehicle_type else None,
        license_plate=driver.license_plate,
        is_available=driver.is_available
    )


@router.post("/availability")
async def toggle_availability(
    is_available: bool,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_driver)
):
    """Toggle driver availability status"""
    result = await session.execute(
        select(Driver).where(Driver.user_id == user.id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    driver.is_available = is_available
    await session.commit()

    return {"message": "Availability updated", "is_available": is_available}

