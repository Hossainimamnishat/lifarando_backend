from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum, DateTime, Numeric, Boolean, ForeignKey, text as sa_text
from app.db.base import Base
import enum


class VehicleType(str, enum.Enum):
    bike = "bike"
    car = "car"


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(Enum(VehicleType))
    hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), index=True
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("CURRENT_TIMESTAMP")
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    geofence_id: Mapped[int | None] = mapped_column(ForeignKey("geofences.id"), nullable=True)


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True
    )
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("CURRENT_TIMESTAMP")
    )
    picked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_km: Mapped[float]
