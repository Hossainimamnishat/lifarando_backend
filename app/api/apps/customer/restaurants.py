"""Customer - browse and search restaurants"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_customer
from app.models.restaurant import Restaurant
from app.models.user import User

router = APIRouter()


class RestaurantListItem(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    cuisine_type: str | None
    lat: float | None
    lon: float | None
    rating: float | None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=list[RestaurantListItem])
async def list_restaurants(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer),
    search: str | None = Query(None, description="Search by name or cuisine"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """List all active restaurants available for ordering"""
    query = select(Restaurant).where(Restaurant.is_active == True)

    if search:
        query = query.where(
            (Restaurant.name.ilike(f"%{search}%")) |
            (Restaurant.cuisine_type.ilike(f"%{search}%"))
        )

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    restaurants = result.scalars().all()

    return [RestaurantListItem.model_validate(r) for r in restaurants]


@router.get("/{restaurant_id}", response_model=RestaurantListItem)
async def get_restaurant_details(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Get details of a specific restaurant"""
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return RestaurantListItem.model_validate(restaurant)

