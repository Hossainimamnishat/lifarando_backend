from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.user import User, UserRole
from app.schemas.auth import SignupIn, LoginIn, TokenOut, RefreshIn
from app.schemas.user import UserOut
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from app.core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=201)
async def signup(data: SignupIn, session: AsyncSession = Depends(get_session)):
    if data.email:
        res = await session.execute(select(User).where(User.email == data.email))
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
    if data.phone:
        res = await session.execute(select(User).where(User.phone == data.phone))
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone already in use")

    user = User(
        email=data.email,
        phone=data.phone,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=None,  # parse ISO date string if you want to store it
        role=UserRole.customer,
        hashed_password=hash_password(data.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn):
    try:
        payload = decode_token(data.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    return TokenOut(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserOut)
async def me(current=Depends(get_current_user)):
    return current
