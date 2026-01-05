"""Customer - shopping cart management"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_customer
from app.models.user import User

router = APIRouter()


class CartItemRequest(BaseModel):
    menu_item_id: int
    quantity: int


class CartResponse(BaseModel):
    items: list[dict]
    subtotal: float


@router.get("/", response_model=CartResponse)
async def get_cart(
    user: User = Depends(get_current_customer)
):
    """Get current cart (session-based or DB-based)"""
    # TODO: Implement cart retrieval from cart_service
    return CartResponse(items=[], subtotal=0.0)


@router.post("/items")
async def add_to_cart(
    data: CartItemRequest,
    user: User = Depends(get_current_customer)
):
    """Add item to cart"""
    # TODO: Implement via cart_service
    return {"message": "Item added to cart", "item_id": data.menu_item_id}


@router.delete("/items/{menu_item_id}")
async def remove_from_cart(
    menu_item_id: int,
    user: User = Depends(get_current_customer)
):
    """Remove item from cart"""
    # TODO: Implement via cart_service
    return {"message": "Item removed from cart"}


@router.delete("/")
async def clear_cart(
    user: User = Depends(get_current_customer)
):
    """Clear entire cart"""
    # TODO: Implement via cart_service
    return {"message": "Cart cleared"}

