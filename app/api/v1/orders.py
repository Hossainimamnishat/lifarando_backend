from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_user
from app.models.order import Order, OrderItem, OrderType, OrderStatus
from app.models.menu import MenuItem
from app.services.pricing_service import Quote

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int


class OrderCreateIn(BaseModel):
    restaurant_id: int
    order_type: OrderType
    items: list[OrderItemIn]
    customer_name: str
    customer_phone: str
    customer_address: str | None = None
    customer_lat: float | None = None
    customer_lon: float | None = None
    delivery_note: str | None = None
    tip: float = 0
    pay_with: str  # paypal|card|bank


@router.post("/", status_code=201)
async def create_order(data: OrderCreateIn, session: AsyncSession = Depends(get_session),
                       user=Depends(get_current_user)):
    # price check like in quote
    ids = [i.menu_item_id for i in data.items]
    res = await session.execute(select(MenuItem).where(MenuItem.id.in_(ids)))
    menu = {m.id: m for m in res.scalars()}
    subtotal = sum(float(menu[i.menu_item_id].price) * i.quantity for i in data.items)
    distance_km = None
    if data.order_type == OrderType.delivery:
        from app.models.restaurant import Restaurant
    r = await session.get(Restaurant, data.restaurant_id)
    if r and r.lat and r.lon and data.customer_lat and data.customer_lon:
        from app.utils.distance import haversine_km
    distance_km = haversine_km(r.lat, r.lon, data.customer_lat, data.customer_lon)
    q = Quote(subtotal=subtotal, distance_km=distance_km, order_type=data.order_type.value)

    order = Order(
        customer_id=user.id,
        restaurant_id=data.restaurant_id,
        order_type=data.order_type,
        status=OrderStatus.created,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        customer_address=data.customer_address,
        customer_lat=data.customer_lat,
        customer_lon=data.customer_lon,
        delivery_note=data.delivery_note,
        subtotal=q.subtotal,
        service_fee=q.service_fee,
        delivery_fee=q.delivery_fee,
        tip=data.tip,
        total=q.total + data.tip,
        distance_km=distance_km,
    )
    session.add(order)
    await session.flush()

    for i in data.items:
        session.add(OrderItem(order_id=order.id, menu_item_id=i.menu_item_id, name=menu[i.menu_item_id].name,
                              quantity=i.quantity, unit_price=menu[i.menu_item_id].price,
                              line_total=float(menu[i.menu_item_id].price) * i.quantity))
    await session.commit()

    # TODO: trigger payment intent via payment_service
    return {"order_id": order.id, "status": order.status}
