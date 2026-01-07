from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, Enum, DateTime, ForeignKey, text as sa_text, Index
from app.db.base import Base
import enum


class OrderType(str, enum.Enum):
    pickup = "pickup"
    delivery = "delivery"


class OrderStatus(str, enum.Enum):
    created = "created"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    assigned = "assigned"
    picked_up = "picked_up"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    rider_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.created)

    customer_name: Mapped[str] = mapped_column(String(150))
    customer_phone: Mapped[str] = mapped_column(String(32))
    customer_address: Mapped[str | None] = mapped_column(String(300))
    customer_lat: Mapped[float | None]
    customer_lon: Mapped[float | None]
    delivery_note: Mapped[str | None] = mapped_column(String(500))

    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    service_fee: Mapped[float] = mapped_column(Numeric(10, 2))
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2))
    tip: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2))

    distance_km: Mapped[float | None]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("CURRENT_TIMESTAMP")
    )

    # Relationships
    city: Mapped["City"] = relationship("City", foreign_keys=[city_id])
    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id])
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", foreign_keys=[restaurant_id])
    rider: Mapped["User | None"] = relationship("User", foreign_keys=[rider_id])
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_orders_city_status', 'city_id', 'status'),
        Index('idx_orders_restaurant_status', 'restaurant_id', 'status'),
        Index('idx_orders_rider_status', 'rider_id', 'status'),
        Index('idx_orders_customer', 'customer_id', 'created_at'),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    name: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int]
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))

    order: Mapped["Order"] = relationship(back_populates="items")
