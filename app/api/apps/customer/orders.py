"""Customer - order placement and tracking"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_customer
from app.models.order import Order, OrderItem, OrderType, OrderStatus
from app.models.menu import MenuItem
from app.models.user import User
from app.services.pricing_service import Quote

router = APIRouter()


class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int


class OrderCreateRequest(BaseModel):
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


class OrderResponse(BaseModel):
    id: int
    restaurant_id: int
    order_type: str
    status: str
    customer_name: str
    customer_phone: str
    customer_address: str | None
    subtotal: float
    service_fee: float
    delivery_fee: float
    tip: float
    total: float
    created_at: str

    class Config:
        from_attributes = True


@router.post("/", response_model=dict, status_code=201)
async def create_order(
    data: OrderCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Place a new order"""
    # Validate and calculate pricing
    ids = [i.menu_item_id for i in data.items]
    res = await session.execute(select(MenuItem).where(MenuItem.id.in_(ids)))
    menu = {m.id: m for m in res.scalars()}

    if len(menu) != len(ids):
        raise HTTPException(status_code=400, detail="Some menu items not found")

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
        session.add(OrderItem(
            order_id=order.id,
            menu_item_id=i.menu_item_id,
            name=menu[i.menu_item_id].name,
            quantity=i.quantity,
            unit_price=menu[i.menu_item_id].price,
            line_total=float(menu[i.menu_item_id].price) * i.quantity
        ))

    await session.commit()

    return {"order_id": order.id, "status": order.status.value, "total": float(order.total)}


@router.get("/", response_model=list[OrderResponse])
async def list_my_orders(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Get all orders for the current customer"""
    result = await session.execute(
        select(Order)
        .where(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    return [
        OrderResponse(
            id=o.id,
            restaurant_id=o.restaurant_id,
            order_type=o.order_type.value,
            status=o.status.value,
            customer_name=o.customer_name,
            customer_phone=o.customer_phone,
            customer_address=o.customer_address,
            subtotal=float(o.subtotal),
            service_fee=float(o.service_fee),
            delivery_fee=float(o.delivery_fee),
            tip=float(o.tip),
            total=float(o.total),
            created_at=o.created_at.isoformat()
        )
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Get details of a specific order"""
    order = await session.get(Order, order_id)

    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=order.id,
        restaurant_id=order.restaurant_id,
        order_type=order.order_type.value,
        status=order.status.value,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_address=order.customer_address,
        subtotal=float(order.subtotal),
        service_fee=float(order.service_fee),
        delivery_fee=float(order.delivery_fee),
        tip=float(order.tip),
        total=float(order.total),
        created_at=order.created_at.isoformat()
    )


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_customer)
):
    """Cancel an order (if allowed)"""
    order = await session.get(Order, order_id)

    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.created, OrderStatus.confirmed]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")

    order.status = OrderStatus.cancelled
    await session.commit()

    return {"message": "Order cancelled successfully", "order_id": order.id}

