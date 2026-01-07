"""
Restaurant Management API with RBAC - Restaurant approval workflow

This demonstrates restaurant admin functionality:
- Restaurant Admin can approve restaurants in their scope
- City Admin can manage restaurants in their cities
- Super Admin has full access
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_user
from app.core.rbac_deps import get_current_user_scopes, ScopeValidator
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.rbac import RoleCode
from app.services.rbac_service import UserScopes

router = APIRouter(prefix="/restaurants-rbac", tags=["Restaurants with RBAC"])


class RestaurantResponse(BaseModel):
    id: int
    city_id: int
    owner_id: int
    name: str
    address: str
    phone: str
    is_approved: bool
    is_active: bool
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RestaurantApprovalRequest(BaseModel):
    approve: bool
    notes: Optional[str] = None


@router.get("/", response_model=list[RestaurantResponse])
async def list_restaurants_scoped(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)],
    city_id: Optional[int] = Query(None),
    pending_approval: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List restaurants with scope filtering

    Access control:
    - **Super Admin**: All restaurants
    - **City Admin**: Restaurants in their cities
    - **Restaurant Admin**: Their own restaurants
    - **Customer/Rider**: Only approved and active restaurants
    """
    query = select(Restaurant)

    # Apply scope-based filters
    if scopes.is_super_admin:
        # Super admin sees everything
        pass
    elif scopes.has_role(RoleCode.CITY_ADMIN, RoleCode.SUPPORT):
        # City-level roles see restaurants in their cities
        query = query.where(Restaurant.city_id.in_(scopes.city_ids))
    elif scopes.has_role(RoleCode.RESTAURANT_ADMIN):
        # Restaurant admin sees their own restaurants
        query = query.where(Restaurant.id.in_(scopes.restaurant_ids))
    elif scopes.has_role(RoleCode.RESTAURANT_OWNER):
        # Restaurant owner sees their own restaurants
        query = query.where(Restaurant.owner_id == user.id)
    else:
        # Customers/riders see only approved and active restaurants
        query = query.where(Restaurant.is_approved == True).where(Restaurant.is_active == True)

    # Apply additional filters
    if city_id:
        if not scopes.is_super_admin and city_id not in scopes.city_ids:
            raise HTTPException(status_code=403, detail=f"No access to city {city_id}")
        query = query.where(Restaurant.city_id == city_id)

    if pending_approval is not None:
        if pending_approval:
            query = query.where(Restaurant.is_approved == False)
        else:
            query = query.where(Restaurant.is_approved == True)

    # Pagination
    query = query.order_by(Restaurant.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    restaurants = result.scalars().all()

    return [RestaurantResponse.model_validate(r) for r in restaurants]


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant_details(
    restaurant_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Get restaurant details with scope validation
    """
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Validate access
    if not scopes.is_super_admin:
        # City admin can access restaurants in their cities
        if scopes.has_role(RoleCode.CITY_ADMIN) and restaurant.city_id in scopes.city_ids:
            pass
        # Restaurant admin can access their restaurants
        elif scopes.has_role(RoleCode.RESTAURANT_ADMIN) and restaurant_id in scopes.restaurant_ids:
            pass
        # Owner can access their restaurant
        elif restaurant.owner_id == user.id:
            pass
        # Others can only access approved restaurants
        elif not restaurant.is_approved or not restaurant.is_active:
            raise HTTPException(status_code=403, detail="Restaurant not accessible")

    return RestaurantResponse.model_validate(restaurant)


@router.post("/{restaurant_id}/approve")
async def approve_restaurant(
    restaurant_id: int,
    data: RestaurantApprovalRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Approve or reject a restaurant

    Access control:
    - **Super Admin**: Can approve any restaurant
    - **Restaurant Admin with RESTAURANT scope**: Can approve restaurants in their scope
    - **City Admin**: Can approve restaurants in their cities
    - **Others**: Not allowed

    This is the key feature requested: Restaurant Admin approves restaurants
    so they can show their food to customers.
    """
    # Check permission
    if not scopes.is_super_admin:
        # Restaurant Admin can approve if they have restaurant scope access
        if scopes.has_role(RoleCode.RESTAURANT_ADMIN):
            if restaurant_id not in scopes.restaurant_ids:
                # City Admin can approve restaurants in their cities
                if not scopes.has_role(RoleCode.CITY_ADMIN):
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to approve this restaurant"
                    )
        elif scopes.has_role(RoleCode.CITY_ADMIN):
            # City admin can approve restaurants in their cities
            pass
        else:
            raise HTTPException(
                status_code=403,
                detail="Only restaurant admins or city admins can approve restaurants"
            )

    # Get restaurant
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Verify city admin has access to this restaurant's city
    if not scopes.is_super_admin and scopes.has_role(RoleCode.CITY_ADMIN):
        if restaurant.city_id not in scopes.city_ids:
            raise HTTPException(
                status_code=403,
                detail="Cannot approve restaurants outside your cities"
            )

    # Update approval status
    restaurant.is_approved = data.approve
    restaurant.approved_by = user.id if data.approve else None
    restaurant.approved_at = datetime.utcnow() if data.approve else None

    # Make active if approved
    if data.approve:
        restaurant.is_active = True

    await session.commit()
    await session.refresh(restaurant)

    return {
        "message": f"Restaurant {'approved' if data.approve else 'rejected'} successfully",
        "restaurant_id": restaurant.id,
        "is_approved": restaurant.is_approved,
        "approved_by": restaurant.approved_by,
        "notes": data.notes
    }


@router.patch("/{restaurant_id}/toggle-active")
async def toggle_restaurant_active(
    restaurant_id: int,
    is_active: bool,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Activate or deactivate a restaurant

    Access control:
    - **Super Admin**: Can toggle any restaurant
    - **City Admin**: Can toggle restaurants in their cities
    - **Restaurant Owner**: Can toggle their own restaurant (if approved)
    """
    restaurant = await session.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Check permission
    if not scopes.is_super_admin:
        if scopes.has_role(RoleCode.CITY_ADMIN):
            if restaurant.city_id not in scopes.city_ids:
                raise HTTPException(status_code=403, detail="No access to this restaurant")
        elif restaurant.owner_id == user.id:
            # Owner can only deactivate if approved
            if not restaurant.is_approved:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot activate restaurant before approval"
                )
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    restaurant.is_active = is_active
    await session.commit()

    return {
        "message": f"Restaurant {'activated' if is_active else 'deactivated'}",
        "restaurant_id": restaurant.id,
        "is_active": is_active
    }


@router.get("/pending-approval/count")
async def get_pending_approval_count(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    scopes: Annotated[UserScopes, Depends(get_current_user_scopes)]
):
    """
    Get count of restaurants pending approval

    Access control:
    - **Super Admin**: Count across all cities
    - **City Admin/Restaurant Admin**: Count in their scope
    """
    query = select(Restaurant).where(Restaurant.is_approved == False)

    # Apply scope filters
    if not scopes.is_super_admin:
        if scopes.has_city_scope():
            query = query.where(Restaurant.city_id.in_(scopes.city_ids))
        elif scopes.has_restaurant_scope():
            query = query.where(Restaurant.id.in_(scopes.restaurant_ids))
        else:
            # No admin access
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await session.execute(query)
    pending_restaurants = result.scalars().all()

    # Group by city
    by_city = {}
    for restaurant in pending_restaurants:
        city_id = restaurant.city_id
        if city_id not in by_city:
            by_city[city_id] = 0
        by_city[city_id] += 1

    return {
        "total_pending": len(pending_restaurants),
        "by_city": by_city
    }

