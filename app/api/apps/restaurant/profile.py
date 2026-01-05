"""Restaurant profile management"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_restaurant_owner
from app.models.user import User
from app.models.restaurant import Restaurant

router = APIRouter()


class RestaurantResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    address: str
    phone: str
    email: str | None
    cuisine_type: str | None
    description: str | None
    lat: float | None
    lon: float | None
    rating: float | None
    is_active: bool

    class Config:
        from_attributes = True


class RestaurantCreateRequest(BaseModel):
    name: str
    address: str
    phone: str
    email: str | None = None
    cuisine_type: str | None = None
    description: str | None = None
    lat: float | None = None
    lon: float | None = None


class RestaurantUpdateRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    cuisine_type: str | None = None
    description: str | None = None
    lat: float | None = None
    lon: float | None = None
    is_active: bool | None = None


@router.get("/", response_model=list[RestaurantResponse])
async def get_my_restaurants(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get all restaurants owned by the current user"""
    result = await session.execute(
        select(Restaurant).where(Restaurant.owner_id == user.id)
    )
    restaurants = result.scalars().all()

    return [RestaurantResponse.model_validate(r) for r in restaurants]


@router.post("/", response_model=RestaurantResponse, status_code=201)
async def create_restaurant(
    data: RestaurantCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Create a new restaurant"""
    restaurant = Restaurant(
        owner_id=user.id,
        name=data.name,
        address=data.address,
        phone=data.phone,
        email=data.email,
        cuisine_type=data.cuisine_type,
        description=data.description,
        lat=data.lat,
        lon=data.lon,
        is_active=True
    )
    session.add(restaurant)
    await session.commit()
    await session.refresh(restaurant)

    return RestaurantResponse.model_validate(restaurant)


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Get restaurant details"""
    restaurant = await session.get(Restaurant, restaurant_id)

    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return RestaurantResponse.model_validate(restaurant)


@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: int,
    data: RestaurantUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_restaurant_owner)
):
    """Update restaurant details"""
    restaurant = await session.get(Restaurant, restaurant_id)

    if not restaurant or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if data.name is not None:
        restaurant.name = data.name
    if data.address is not None:
        restaurant.address = data.address
    if data.phone is not None:
        restaurant.phone = data.phone
    if data.email is not None:
        restaurant.email = data.email
    if data.cuisine_type is not None:
        restaurant.cuisine_type = data.cuisine_type
    if data.description is not None:
        restaurant.description = data.description
    if data.lat is not None:
        restaurant.lat = data.lat
    if data.lon is not None:
        restaurant.lon = data.lon
    if data.is_active is not None:
        restaurant.is_active = data.is_active

    await session.commit()
    await session.refresh(restaurant)

    return RestaurantResponse.model_validate(restaurant)

