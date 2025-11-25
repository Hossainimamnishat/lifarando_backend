from __future__ import annotations
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum, Date, Boolean
from app.db.base import Base
import enum


class UserRole(str, enum.Enum):
    customer = "customer"
    restaurant_owner = "restaurant_owner"
    driver = "driver"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.customer)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
