"""
RBAC Admin API - Manage roles and permissions

These endpoints allow super admins and city admins to manage user roles:
- List/create/update roles
- Assign/revoke user roles
- Manage shift leads and their constraints
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session, get_current_user
from app.core.rbac_deps import require_super_admin, require_city_admin, ScopeValidator
from app.models.user import User
from app.models.rbac import Role, UserRole as UserRoleModel, ScopeType, RoleCode, City, ShiftLead
from app.services.rbac_service import UserScopes, get_user_scopes, can_assign_role

router = APIRouter(prefix="/rbac", tags=["RBAC Admin"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class RoleCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scope_type: ScopeType


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    scope_type: ScopeType
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserRoleAssign(BaseModel):
    user_id: int
    role_code: str
    city_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    notes: Optional[str] = None


class UserRoleResponse(BaseModel):
    id: int
    user_id: int
    role_code: str
    role_name: str
    city_id: Optional[int]
    restaurant_id: Optional[int]
    is_active: bool
    assigned_at: datetime
    assigned_by: Optional[int]
    notes: Optional[str]

    class Config:
        from_attributes = True


class CityCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    country: str = Field(..., max_length=100)
    timezone: str = Field(..., max_length=50)


class CityResponse(BaseModel):
    id: int
    name: str
    code: str
    country: str
    timezone: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ShiftLeadCreate(BaseModel):
    user_id: int
    city_id: int
    min_hours_per_shift: int = Field(default=4, ge=1, le=24)
    max_hours_per_shift: int = Field(default=12, ge=1, le=24)
    min_hours_per_week: int = Field(default=20, ge=1, le=168)
    max_hours_per_week: int = Field(default=60, ge=1, le=168)


class ShiftLeadResponse(BaseModel):
    id: int
    user_id: int
    city_id: int
    min_hours_per_shift: int
    max_hours_per_shift: int
    min_hours_per_week: int
    max_hours_per_week: int
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Role Management Endpoints (Super Admin Only)
# ============================================================================

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    session: Annotated[AsyncSession, Depends(get_session)],
    scopes: Annotated[UserScopes, Depends(require_super_admin)],
    include_inactive: bool = Query(False)
):
    """
    List all roles in the system

    - **Super Admin only**
    """
    query = select(Role)
    if not include_inactive:
        query = query.where(Role.is_active == True)

    result = await session.execute(query.order_by(Role.code))
    roles = result.scalars().all()

    return [RoleResponse.model_validate(role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    data: RoleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    scopes: Annotated[UserScopes, Depends(require_super_admin)]
):
    """
    Create a new role

    - **Super Admin only**
    """
    # Check if role code already exists
    existing = await session.execute(
        select(Role).where(Role.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role code already exists")

    role = Role(
        code=data.code,
        name=data.name,
        description=data.description,
        scope_type=data.scope_type,
        is_active=True
    )

    session.add(role)
    await session.commit()
    await session.refresh(role)

    return RoleResponse.model_validate(role)


@router.patch("/roles/{role_id}")
async def toggle_role_status(
    role_id: int,
    is_active: bool,
    session: Annotated[AsyncSession, Depends(get_session)],
    scopes: Annotated[UserScopes, Depends(require_super_admin)]
):
    """
    Activate or deactivate a role

    - **Super Admin only**
    """
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.is_active = is_active
    await session.commit()

    return {"message": "Role status updated", "is_active": is_active}


# ============================================================================
# User Role Assignment Endpoints
# ============================================================================

@router.get("/user-roles", response_model=list[UserRoleResponse])
async def list_user_roles(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    user_id: Optional[int] = Query(None),
    city_id: Optional[int] = Query(None),
    include_inactive: bool = Query(False)
):
    """
    List user role assignments

    - **Super Admin**: Can see all
    - **City Admin**: Can see roles in their cities
    - **Others**: Can see only their own roles
    """
    scopes = await get_user_scopes(session, user.id)

    query = select(UserRoleModel, Role).join(Role, UserRoleModel.role_id == Role.id)

    # Apply filters based on permissions
    if not scopes.is_super_admin:
        if scopes.has_role(RoleCode.CITY_ADMIN):
            # City admins can only see roles in their cities
            query = query.where(UserRoleModel.city_id.in_(scopes.city_ids))
        else:
            # Others can only see their own roles
            query = query.where(UserRoleModel.user_id == user.id)

    # Apply additional filters
    if user_id:
        query = query.where(UserRoleModel.user_id == user_id)

    if city_id:
        query = query.where(UserRoleModel.city_id == city_id)

    if not include_inactive:
        query = query.where(UserRoleModel.is_active == True)

    result = await session.execute(query)
    user_roles = result.all()

    return [
        UserRoleResponse(
            id=ur.id,
            user_id=ur.user_id,
            role_code=role.code,
            role_name=role.name,
            city_id=ur.city_id,
            restaurant_id=ur.restaurant_id,
            is_active=ur.is_active,
            assigned_at=ur.assigned_at,
            assigned_by=ur.assigned_by,
            notes=ur.notes
        )
        for ur, role in user_roles
    ]


@router.post("/user-roles", status_code=201)
async def assign_user_role(
    data: UserRoleAssign,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)]
):
    """
    Assign a role to a user

    - **Super Admin**: Can assign any role
    - **City Admin**: Can assign city-scoped roles in their cities
    """
    # Check if assigner has permission
    allowed = await can_assign_role(
        session,
        user.id,
        data.role_code,
        data.city_id,
        data.restaurant_id
    )

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to assign this role"
        )

    # Get the role
    result = await session.execute(
        select(Role).where(Role.code == data.role_code).where(Role.is_active == True)
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify target user exists
    target_user = await session.get(User, data.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate scope constraints
    if role.scope_type == ScopeType.GLOBAL and (data.city_id or data.restaurant_id):
        raise HTTPException(status_code=400, detail="Global roles cannot have city or restaurant scope")

    if role.scope_type == ScopeType.CITY:
        if not data.city_id:
            raise HTTPException(status_code=400, detail="City ID required for city-scoped role")
        if data.restaurant_id:
            raise HTTPException(status_code=400, detail="City-scoped roles cannot have restaurant scope")

    if role.scope_type == ScopeType.RESTAURANT and not data.restaurant_id:
        raise HTTPException(status_code=400, detail="Restaurant ID required for restaurant-scoped role")

    # Check if assignment already exists
    existing = await session.execute(
        select(UserRoleModel).where(
            UserRoleModel.user_id == data.user_id,
            UserRoleModel.role_id == role.id,
            UserRoleModel.city_id == data.city_id,
            UserRoleModel.restaurant_id == data.restaurant_id,
            UserRoleModel.is_active == True
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role already assigned with this scope")

    # Create assignment
    user_role = UserRoleModel(
        user_id=data.user_id,
        role_id=role.id,
        city_id=data.city_id,
        restaurant_id=data.restaurant_id,
        is_active=True,
        assigned_by=user.id,
        notes=data.notes
    )

    session.add(user_role)
    await session.commit()
    await session.refresh(user_role)

    return {
        "message": "Role assigned successfully",
        "user_role_id": user_role.id
    }


@router.delete("/user-roles/{user_role_id}")
async def revoke_user_role(
    user_role_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)]
):
    """
    Revoke a user's role assignment

    - **Super Admin**: Can revoke any role
    - **City Admin**: Can revoke city-scoped roles in their cities
    """
    user_role = await session.get(UserRoleModel, user_role_id)
    if not user_role:
        raise HTTPException(status_code=404, detail="User role assignment not found")

    scopes = await get_user_scopes(session, user.id)

    # Check permission
    if not scopes.is_super_admin:
        if scopes.has_role(RoleCode.CITY_ADMIN):
            # City admin can only revoke roles in their cities
            if user_role.city_id not in scopes.city_ids:
                raise HTTPException(status_code=403, detail="Cannot revoke roles outside your cities")
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    user_role.is_active = False
    user_role.revoked_at = datetime.utcnow()
    await session.commit()

    return {"message": "Role revoked successfully"}


# ============================================================================
# City Management Endpoints
# ============================================================================

@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    include_inactive: bool = Query(False)
):
    """
    List cities

    - **Super Admin**: Can see all cities
    - **City Admin/Others**: Can see cities they have access to
    """
    scopes = await get_user_scopes(session, user.id)

    query = select(City)

    # Filter by scope
    if not scopes.is_super_admin and scopes.city_ids:
        query = query.where(City.id.in_(scopes.city_ids))

    if not include_inactive:
        query = query.where(City.is_active == True)

    result = await session.execute(query.order_by(City.name))
    cities = result.scalars().all()

    return [CityResponse.model_validate(city) for city in cities]


@router.post("/cities", response_model=CityResponse, status_code=201)
async def create_city(
    data: CityCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    scopes: Annotated[UserScopes, Depends(require_super_admin)]
):
    """
    Create a new city

    - **Super Admin only**
    """
    # Check if code already exists
    existing = await session.execute(
        select(City).where(City.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="City code already exists")

    city = City(
        name=data.name,
        code=data.code,
        country=data.country,
        timezone=data.timezone,
        is_active=True
    )

    session.add(city)
    await session.commit()
    await session.refresh(city)

    return CityResponse.model_validate(city)


# ============================================================================
# Shift Lead Management Endpoints
# ============================================================================

@router.post("/shift-leads", response_model=ShiftLeadResponse, status_code=201)
async def create_shift_lead(
    data: ShiftLeadCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)]
):
    """
    Create a shift lead for a city

    - **Super Admin**: Can create for any city
    - **City Admin**: Can create only for their cities
    """
    scopes = await get_user_scopes(session, user.id)

    # Check permission
    if not scopes.is_super_admin:
        if not scopes.has_role(RoleCode.CITY_ADMIN) or data.city_id not in scopes.city_ids:
            raise HTTPException(status_code=403, detail="Cannot create shift lead for this city")

    # Verify user exists
    target_user = await session.get(User, data.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify city exists
    city = await session.get(City, data.city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    # Check if already exists
    existing = await session.execute(
        select(ShiftLead).where(
            ShiftLead.user_id == data.user_id,
            ShiftLead.city_id == data.city_id,
            ShiftLead.is_active == True
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Shift lead already exists for this user and city")

    # Validate constraints
    if data.min_hours_per_shift > data.max_hours_per_shift:
        raise HTTPException(status_code=400, detail="Min hours cannot exceed max hours per shift")

    if data.min_hours_per_week > data.max_hours_per_week:
        raise HTTPException(status_code=400, detail="Min hours cannot exceed max hours per week")

    shift_lead = ShiftLead(
        user_id=data.user_id,
        city_id=data.city_id,
        min_hours_per_shift=data.min_hours_per_shift,
        max_hours_per_shift=data.max_hours_per_shift,
        min_hours_per_week=data.min_hours_per_week,
        max_hours_per_week=data.max_hours_per_week,
        is_active=True
    )

    session.add(shift_lead)

    # Also assign shift_lead role if not already assigned
    role_result = await session.execute(
        select(Role).where(Role.code == RoleCode.SHIFT_LEAD)
    )
    role = role_result.scalar_one_or_none()

    if role:
        # Check if role already assigned
        existing_role = await session.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == data.user_id,
                UserRoleModel.role_id == role.id,
                UserRoleModel.city_id == data.city_id,
                UserRoleModel.is_active == True
            )
        )
        if not existing_role.scalar_one_or_none():
            user_role = UserRoleModel(
                user_id=data.user_id,
                role_id=role.id,
                city_id=data.city_id,
                assigned_by=user.id,
                is_active=True
            )
            session.add(user_role)

    await session.commit()
    await session.refresh(shift_lead)

    return ShiftLeadResponse.model_validate(shift_lead)


@router.get("/shift-leads", response_model=list[ShiftLeadResponse])
async def list_shift_leads(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    city_id: Optional[int] = Query(None)
):
    """
    List shift leads

    - **Super Admin**: Can see all
    - **City Admin**: Can see shift leads in their cities
    """
    scopes = await get_user_scopes(session, user.id)

    query = select(ShiftLead).where(ShiftLead.is_active == True)

    # Apply scope filters
    if not scopes.is_super_admin:
        if scopes.has_role(RoleCode.CITY_ADMIN):
            query = query.where(ShiftLead.city_id.in_(scopes.city_ids))
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    if city_id:
        query = query.where(ShiftLead.city_id == city_id)

    result = await session.execute(query)
    shift_leads = result.scalars().all()

    return [ShiftLeadResponse.model_validate(sl) for sl in shift_leads]

