from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, ForeignKey
from app.db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150), index=True)
    ingredients: Mapped[str] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    picture_url: Mapped[str | None] = mapped_column(String(500))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
