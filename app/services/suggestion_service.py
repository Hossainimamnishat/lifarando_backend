from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.menu import MenuItem


async def suggest_items(session: AsyncSession, restaurant_id: int, exclude_ids: list[int], limit: int = 5):
    res = await session.execute(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id, ~MenuItem.id.in_(exclude_ids)).order_by(
            MenuItem.sales_count.desc()).limit(limit)
    )
    return [
        {"id": m.id, "name": m.name, "price": float(m.price), "picture_url": m.picture_url}
        for m in res.scalars()
    ]
