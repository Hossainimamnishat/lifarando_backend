from app.models.payment import PaymentProvider, PaymentStatus, Payment
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_intent(self, order_id: int, amount: float, provider: PaymentProvider) -> Payment:
        p = Payment(order_id=order_id, provider=provider, status=PaymentStatus.pending, amount=amount, currency="EUR", created_at=datetime.utcnow())
        self.session.add(p)
        await self.session.commit()
        return p


    async def capture(self, payment_id: int) -> None:
        p = await self.session.get(Payment, payment_id)
        p.status = PaymentStatus.captured
        await self.session.commit()


    async def refund(self, payment_id: int, amount: float, reason: str | None = None) -> None:
        from app.models.payment import Refund
        p = await self.session.get(Payment, payment_id)
        self.session.add(Refund(payment_id=payment_id, amount=amount, reason=reason))
        p.status = PaymentStatus.refunded
        await self.session.commit()