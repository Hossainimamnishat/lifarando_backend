"""Restaurant owner authentication endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_session
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, UserRole

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    first_name: str
    last_name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_restaurant_owner(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session)
):
    """Register a new restaurant owner account"""
    if not data.email and not data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone is required"
        )

    # Check if user already exists
    query = select(User)
    if data.email:
        query = query.where(User.email == data.email)
    else:
        query = query.where(User.phone == data.phone)

    existing = await session.execute(query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    # Create restaurant owner user
    user = User(
        email=data.email,
        phone=data.phone,
        first_name=data.first_name,
        last_name=data.last_name,
        hashed_password=hash_password(data.password),
        role=UserRole.restaurant_owner,
        is_active=True
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        role=user.role.value
    )


@router.post("/login", response_model=TokenResponse)
async def login_restaurant_owner(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """Login for restaurant owner users"""
    if not data.email and not data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone is required"
        )

    # Find user
    query = select(User).where(User.role == UserRole.restaurant_owner)
    if data.email:
        query = query.where(User.email == data.email)
    else:
        query = query.where(User.phone == data.phone)

    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        role=user.role.value
    )

