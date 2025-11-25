from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum, Numeric, DateTime, ForeignKey, text as sa_text
from app.db.base import Base
import enum


class PaymentProvider(str, enum.Enum):
    paypal = "paypal"
    card = "card"   # Stripe or other PSP underneath
    bank = "bank"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    authorized = "authorized"
    captured = "captured"
    refunded = "refunded"
    failed = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True
    )
    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("CURRENT_TIMESTAMP")
    )


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("CURRENT_TIMESTAMP")
    )
