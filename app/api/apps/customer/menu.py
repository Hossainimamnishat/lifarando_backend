"""Customer - browse menu items"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_customer
from app.models.menu import MenuItem
from app.models.user import User

router = APIRouter()


class MenuItemResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: str | None
    price: float
    category: str | None
    is_available: bool
    image_url: str | None

    class Config:
        from_attributes = True


@router.get("/restaurant/{restaurant_id}", response_model=list[MenuItemResponse])
async def get_restaurant_menu(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer),
    category: str | None = Query(None, description="Filter by category"),
    available_only: bool = Query(True, description="Show only available items")
):
    """Get menu items for a specific restaurant"""
    query = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)

    if available_only:
        query = query.where(MenuItem.is_available == True)

    if category:
        query = query.where(MenuItem.category == category)

    result = await session.execute(query)
    items = result.scalars().all()

    return [MenuItemResponse.model_validate(item) for item in items]


@router.get("/item/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Get details of a specific menu item"""
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    return MenuItemResponse.model_validate(item)

