from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_session, get_current_user
from app.models import MenuItem
from app.services.suggestion_service import suggest_items
from app.services.pricing_service import Quote

router = APIRouter(prefix="/cart", tags=["cart"])


class CartItemIn(BaseModel):
    menu_item_id: int
    quantity: int


class CartQuoteIn(BaseModel):
    restaurant_id: int
    items: list[CartItemIn]
    order_type: str  # pickup|delivery
    customer_lat: float | None = None
    customer_lon: float | None = None


@router.post("/quote")
async def quote(data: CartQuoteIn, session: AsyncSession = Depends(get_session)):
    # fetch prices & compute subtotal
    from sqlalchemy import select
    ids = [i.menu_item_id for i in data.items]
    res = await session.execute(select(MenuItem).where(MenuItem.id.in_(ids)))
    menu = {m.id: m for m in res.scalars()}
    subtotal = sum(float(menu[i.menu_item_id].price) * i.quantity for i in data.items)

    # distance
    from app.models.restaurant import Restaurant
    r = await session.get(Restaurant, data.restaurant_id)
    distance_km = None
    if data.order_type == "delivery" and r and r.lat and r.lon and data.customer_lat and data.customer_lon:
        from app.utils.distance import haversine_km
    distance_km = haversine_km(r.lat, r.lon, data.customer_lat, data.customer_lon)

    q = Quote(subtotal=subtotal, distance_km=distance_km, order_type=data.order_type)

    suggestions = await suggest_items(session, data.restaurant_id, exclude_ids=ids)

    return {
        "subtotal": q.subtotal,
        "service_fee": q.service_fee,
        "delivery_fee": q.delivery_fee,
        "total": q.total,
        "distance_km": distance_km,
        "suggested_items": suggestions,
    }
