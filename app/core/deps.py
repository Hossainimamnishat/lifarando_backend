from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.user import User, UserRole
from app.core.security import decode_token

AuthBearer = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(AuthBearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = int(payload.get("sub", 0))
    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


# Role-based dependencies for app-specific access control
async def get_current_customer(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure the current user is a customer"""
    if user.role != UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required"
        )
    return user


async def get_current_driver(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure the current user is a driver/rider"""
    if user.role != UserRole.driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver access required"
        )
    return user


async def get_current_restaurant_owner(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure the current user is a restaurant owner"""
    if user.role != UserRole.restaurant_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant owner access required"
        )
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure the current user is an admin"""
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

