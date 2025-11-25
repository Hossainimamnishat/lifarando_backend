from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Integer
from app.db.base import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    license_id: Mapped[str | None] = mapped_column(String(100), index=True)
    phone: Mapped[str] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str] = mapped_column(String(120))
    banner_url: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[str] = mapped_column(String(300))
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    hours: Mapped[list["BusinessHour"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )


class BusinessHour(Base):
    __tablename__ = "business_hours"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer)        # 0=Mon ... 6=Sun
    open_time: Mapped[str] = mapped_column(String(5))    # "09:00"
    close_time: Mapped[str] = mapped_column(String(5))   # "21:00"

    restaurant: Mapped["Restaurant"] = relationship(back_populates="hours")
