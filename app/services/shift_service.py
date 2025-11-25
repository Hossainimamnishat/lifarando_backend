# app/services/shift_service.py
from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.driver import Shift, Delivery


def _overlap_minutes(start: datetime, end: Optional[datetime], win_start: datetime, win_end: datetime) -> int:
    """
    Return the number of minutes a [start, end] interval overlaps with [win_start, win_end].
    If end is None (open shift), treat it as win_end for overlap purposes.
    """
    real_end = end or win_end
    # No overlap
    if real_end <= win_start or start >= win_end:
        return 0
    # Clamp to window
    s = max(start, win_start)
    e = min(real_end, win_end)
    return max(0, int((e - s).total_seconds() // 60))


async def minutes_worked(
    session: AsyncSession,
    driver_id: int,
    since: datetime,
    until: datetime
) -> int:
    """
    Sum minutes the driver was on shift overlapping [since, until].
    """
    res = await session.execute(
        select(Shift).where(Shift.driver_id == driver_id)
    )
    total = 0
    for shift in res.scalars():
        total += _overlap_minutes(shift.starts_at, shift.ends_at, since, until)
    return total


async def delivered_count(
    session: AsyncSession,
    driver_id: int,
    since: datetime,
    until: datetime
) -> int:
    """
    Count deliveries completed in [since, until].
    """
    res = await session.execute(
        select(func.count())
        .select_from(Delivery)
        .where(
            and_(
                Delivery.driver_id == driver_id,
                Delivery.delivered_at.is_not(None),
                Delivery.delivered_at >= since,
                Delivery.delivered_at <= until,
            )
        )
    )
    return int(res.scalar_one())


async def apply_bonus_if_needed(session: AsyncSession, driver_id: int) -> bool:
    """
    If the driver has completed a multiple of BONUS_EVERY_N_ORDERS total deliveries,
    issue a bonus (placeholder) and return True. Otherwise return False.
    """
    res = await session.execute(
        select(func.count())
        .select_from(Delivery)
        .where(Delivery.driver_id == driver_id, Delivery.delivered_at.is_not(None))
    )
    count = int(res.scalar_one())

    if count > 0 and settings.BONUS_EVERY_N_ORDERS > 0 and count % settings.BONUS_EVERY_N_ORDERS == 0:
        # TODO: persist a payout row; for now just log/print
        # You could insert into a payouts table here and commit.
        print(f"Bonus {settings.BONUS_AMOUNT} issued to driver {driver_id} (completed {count} deliveries)")
        return True
    return False
