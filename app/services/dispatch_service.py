from sqlalchemy.ext.asyncio import AsyncSession
from app.models.driver import Driver, VehicleType
from app.services.pricing_service import driver_eligible


async def find_eligible_drivers(session: AsyncSession, distance_km: float) -> list[int]:
    from sqlalchemy import select
    res = await session.execute(select(Driver))
    drivers = [d for d in res.scalars() if driver_eligible(d.vehicle_type.value, distance_km)]
    return [d.id for d in drivers]
