"""Restaurant menu management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_restaurant_owner
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.menu import MenuItem

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


class MenuItemCreateRequest(BaseModel):
    restaurant_id: int
    name: str
    description: str | None = None
    price: float
    category: str | None = None
    is_available: bool = True
    image_url: str | None = None


class MenuItemUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category: str | None = None
    is_available: bool | None = None
    image_url: str | None = None


@router.get("/restaurant/{restaurant_id}", response_model=list[MenuItemResponse])
async def get_menu_items(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get all menu items for a restaurant"""
    # Verify ownership
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    result = await session.execute(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    )
    items = result.scalars().all()

    return [MenuItemResponse.model_validate(item) for item in items]


@router.post("/", response_model=MenuItemResponse, status_code=201)
async def create_menu_item(
    data: MenuItemCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Create a new menu item"""
    # Verify ownership
    restaurant = await session.get(Restaurant, data.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this restaurant")

    menu_item = MenuItem(
        restaurant_id=data.restaurant_id,
        name=data.name,
        description=data.description,
        price=data.price,
        category=data.category,
        is_available=data.is_available,
        image_url=data.image_url
    )
    session.add(menu_item)
    await session.commit()
    await session.refresh(menu_item)

    return MenuItemResponse.model_validate(menu_item)


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get menu item details"""
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, item.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Menu item not found")

    return MenuItemResponse.model_validate(item)


@router.patch("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: int,
    data: MenuItemUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Update menu item"""
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, item.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if data.name is not None:
        item.name = data.name
    if data.description is not None:
        item.description = data.description
    if data.price is not None:
        item.price = data.price
    if data.category is not None:
        item.category = data.category
    if data.is_available is not None:
        item.is_available = data.is_available
    if data.image_url is not None:
        item.image_url = data.image_url

    await session.commit()
    await session.refresh(item)

    return MenuItemResponse.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_menu_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Delete menu item"""
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Verify ownership
    restaurant = await session.get(Restaurant, item.restaurant_id)
    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await session.delete(item)
    await session.commit()

    return None

