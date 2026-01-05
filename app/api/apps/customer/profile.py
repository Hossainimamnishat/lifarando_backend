"""Customer profile management"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from datetime import date

from app.core.deps import get_session, get_current_customer
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class ProfileResponse(BaseModel):
    id: int
    email: str | None
    phone: str | None
    first_name: str
    last_name: str
    date_of_birth: date | None
    role: str

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    phone: str | None = None


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    user: User = Depends(get_current_customer)
):
    """Get current customer profile"""
    return ProfileResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=user.date_of_birth,
        role=user.role.value
    )


@router.patch("/", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Update customer profile"""
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.date_of_birth is not None:
        user.date_of_birth = data.date_of_birth
    if data.phone is not None:
        user.phone = data.phone

    await session.commit()
    await session.refresh(user)

    return ProfileResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=user.date_of_birth,
        role=user.role.value
    )

