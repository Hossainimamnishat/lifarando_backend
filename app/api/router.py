"""
Main API router that organizes endpoints by app (customer, rider, restaurant)
Each app has its own router with role-based access control
"""
from fastapi import APIRouter

# Import app-specific routers
from app.api.apps.customer import router as customer_router
from app.api.apps.rider import router as rider_router
from app.api.apps.restaurant import router as restaurant_router

# Import RBAC admin routers
from app.api.v1 import rbac_admin, orders_rbac, restaurants_rbac, dashboard

api_router = APIRouter()

# === APP-SPECIFIC ROUTERS ===
# Each app has its own dedicated prefix and endpoints

# Customer App - for end users placing orders
api_router.include_router(
    customer_router,
    prefix="/customer",
    tags=["Customer App"]
)

# Rider App - for delivery drivers/riders
api_router.include_router(
    rider_router,
    prefix="/rider",
    tags=["Rider App"]
)

# Restaurant App - for restaurant owners/managers
api_router.include_router(
    restaurant_router,
    prefix="/restaurant",
    tags=["Restaurant App"]
)

# === RBAC & ADMIN ENDPOINTS ===
# Role-based access control and admin management

api_router.include_router(dashboard.router)
api_router.include_router(rbac_admin.router)
api_router.include_router(orders_rbac.router)
api_router.include_router(restaurants_rbac.router)

# === SHARED/ADMIN ENDPOINTS ===
# Legacy v1 endpoints (if needed for backwards compatibility)
# from .v1 import payments, webhooks
# api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
# api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# Health check endpoint
@api_router.get("/health", tags=["System"])
async def health():
    """System health check"""
    return {
        "status": "ok",
        "apps": ["customer", "rider", "restaurant"],
        "features": ["rbac", "multi_city", "restaurant_approval", "shift_management"]
    }
