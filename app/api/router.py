from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])


# v1 routers will be added here as modules are created:
# from .v1 import auth, users, restaurants, menu, cart, orders, drivers, payments, webhooks
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
# api_router.include_router(menu.router, prefix="/menu", tags=["menu"])
# api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
# api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
# api_router.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
# api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
# api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# Temporary health endpoint so you can hit something immediately
@api_router.get("/health", tags=["_internal"])
async def health():
    return {"status": "ok"}
