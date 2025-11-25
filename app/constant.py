from enum import Enum

# Roles used across the app (mirrors models later)
class UserRole(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_OWNER = "restaurant_owner"
    DRIVER = "driver"
    ADMIN = "admin"

# Order types / status (duplicated here for early use; models will import their own enums)
class OrderType(str, Enum):
    PICKUP = "pickup"
    DELIVERY = "delivery"

class OrderStatus(str, Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

# Driver vehicles and simple limits (config-driven limits live in settings)
class VehicleType(str, Enum):
    BIKE = "bike"
    CAR = "car"

# UI-friendly preset tips (can accept custom too)
TIP_PRESETS_EUR = [1, 2, 4, 5]

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
