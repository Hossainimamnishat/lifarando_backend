"""Rider/Driver App API endpoints - for delivery personnel"""
from fastapi import APIRouter
from . import auth, profile, shifts, deliveries, earnings

router = APIRouter()

# Rider app routes
router.include_router(auth.router, prefix="/auth", tags=["rider:auth"])
router.include_router(profile.router, prefix="/profile", tags=["rider:profile"])
router.include_router(shifts.router, prefix="/shifts", tags=["rider:shifts"])
router.include_router(deliveries.router, prefix="/deliveries", tags=["rider:deliveries"])
router.include_router(earnings.router, prefix="/earnings", tags=["rider:earnings"])

