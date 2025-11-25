from app.config import settings
from app.utils.distance import haversine_km


class Quote:
    def __init__(self, subtotal: float, distance_km: float | None, order_type: str):
        self.subtotal = round(subtotal, 2)
        self.service_fee = round(subtotal * settings.SERVICE_FEE_RATE, 2)
        self.delivery_fee = 0.0
        if order_type == "delivery" and distance_km is not None:
            self.delivery_fee = round(settings.DELIVERY_BASE_FEE + distance_km * settings.DELIVERY_PER_KM_FEE, 2)
        self.total = round(self.subtotal + self.service_fee + self.delivery_fee, 2)


def driver_eligible(vehicle: str, distance_km: float) -> bool:
    if vehicle == "bike":
        return distance_km <= settings.BIKE_MAX_KM
    if vehicle == "car":
        return distance_km <= settings.CAR_MAX_KM
    return False
