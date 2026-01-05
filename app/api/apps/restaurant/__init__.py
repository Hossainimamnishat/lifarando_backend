"""Restaurant App API endpoints - for restaurant owners/managers"""
from fastapi import APIRouter
from . import auth, profile, menu, orders, business_hours, analytics

router = APIRouter()

# Restaurant app routes
router.include_router(auth.router, prefix="/auth", tags=["restaurant:auth"])
router.include_router(profile.router, prefix="/profile", tags=["restaurant:profile"])
router.include_router(menu.router, prefix="/menu", tags=["restaurant:menu"])
router.include_router(orders.router, prefix="/orders", tags=["restaurant:orders"])
router.include_router(business_hours.router, prefix="/business-hours", tags=["restaurant:business-hours"])
router.include_router(analytics.router, prefix="/analytics", tags=["restaurant:analytics"])

