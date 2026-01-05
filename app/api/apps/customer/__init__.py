"""Customer App API endpoints - for end users placing orders"""
from fastapi import APIRouter
from . import auth, restaurants, menu, cart, orders, profile

router = APIRouter()

# Customer app routes
router.include_router(auth.router, prefix="/auth", tags=["customer:auth"])
router.include_router(profile.router, prefix="/profile", tags=["customer:profile"])
router.include_router(restaurants.router, prefix="/restaurants", tags=["customer:restaurants"])
router.include_router(menu.router, prefix="/menu", tags=["customer:menu"])
router.include_router(cart.router, prefix="/cart", tags=["customer:cart"])
router.include_router(orders.router, prefix="/orders", tags=["customer:orders"])

