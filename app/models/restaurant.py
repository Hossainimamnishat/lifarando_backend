from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Integer, DateTime, Index
from app.db.base import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

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
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.12)
    cuisine_type: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2))

    # Approval workflow
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    city: Mapped["City"] = relationship("City", foreign_keys=[city_id])
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])
    hours: Mapped[list["BusinessHour"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_restaurants_city_active', 'city_id', 'is_active'),
        Index('idx_restaurants_owner', 'owner_id'),
        Index('idx_restaurants_approved', 'is_approved', 'is_active'),
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
