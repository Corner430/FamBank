"""WishList API endpoints: CRUD for wish lists and items. §4.2, §4.3"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ChildId, FamilyContext, ParentContext
from app.database import get_db
from app.schemas.common import cents_to_yuan, yuan_to_cents
from app.schemas.wishlist import (
    DeclareTargetRequest,
    WishItemPriceUpdate,
    WishItemResponse,
    WishListCreateRequest,
    WishListResponse,
    WishListTargetResponse,
)
from app.services.wishlist import (
    clear_target,
    create_wish_list,
    declare_target,
    get_active_wish_list,
    update_item_price,
)

router = APIRouter(tags=["wishlist"])


def _item_to_response(item) -> WishItemResponse:
    return WishItemResponse(
        id=item.id,
        name=item.name,
        registered_price=cents_to_yuan(item.registered_price),
        current_price=cents_to_yuan(item.current_price),
        last_price_update=item.last_price_update.isoformat() if item.last_price_update else None,
        verification_url=item.verification_url,
    )


def _wishlist_to_response(wish_list, items, p_active: int) -> WishListResponse:
    return WishListResponse(
        id=wish_list.id,
        status=wish_list.status,
        registered_at=wish_list.registered_at.isoformat(),
        lock_until=wish_list.lock_until.isoformat(),
        valid_until=wish_list.valid_until.isoformat(),
        avg_price=cents_to_yuan(wish_list.avg_price),
        max_price=cents_to_yuan(wish_list.max_price),
        p_active=cents_to_yuan(p_active),
        active_target_item_id=wish_list.active_target_item_id,
        items=[_item_to_response(i) for i in items],
    )


@router.get("/wishlist", response_model=WishListResponse | None)
async def get_wishlist(
    child_id_resolved: ChildId,
    ctx: FamilyContext,
    db: AsyncSession = Depends(get_db),
):
    """Get current active wish list with items. §4.2"""
    result = await get_active_wish_list(
        db,
        family_id=ctx.family_id,
        user_id=child_id_resolved,
    )
    if result is None:
        return None

    return _wishlist_to_response(
        result["wish_list"], result["items"], result["p_active"]
    )


@router.post("/wishlist", response_model=WishListResponse)
async def create_wishlist(
    req: WishListCreateRequest,
    child_id_resolved: ChildId,
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """Create a new wish list with items. §4.2"""
    if not req.items:
        raise HTTPException(status_code=400, detail="愿望清单不能为空")

    try:
        items_data = []
        for item in req.items:
            price_cents = yuan_to_cents(item.price)
            if price_cents <= 0:
                raise ValueError(f"物品 '{item.name}' 的价格必须为正数")
            items_data.append({
                "name": item.name,
                "price": price_cents,
                "verification_url": item.verification_url,
            })
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await create_wish_list(
            db, items_data,
            family_id=ctx.family_id,
            user_id=child_id_resolved,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _wishlist_to_response(
        result["wish_list"], result["items"], result["p_active"]
    )


@router.patch("/wishlist/items/{item_id}/price", response_model=WishItemResponse)
async def update_item_price_endpoint(
    item_id: int,
    req: WishItemPriceUpdate,
    child_id_resolved: ChildId,
    ctx: FamilyContext,
    db: AsyncSession = Depends(get_db),
):
    """Update a wish item's price. Once per month per item. §4.2"""
    try:
        new_price_cents = yuan_to_cents(req.price)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        item = await update_item_price(
            db, item_id, new_price_cents,
            family_id=ctx.family_id,
            user_id=child_id_resolved,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _item_to_response(item)


@router.post("/wishlist/declare-target", response_model=WishListTargetResponse)
async def declare_target_endpoint(
    req: DeclareTargetRequest,
    child_id_resolved: ChildId,
    ctx: FamilyContext,
    db: AsyncSession = Depends(get_db),
):
    """Declare a wish item as the active target. §4.3"""
    try:
        result = await declare_target(
            db, req.wish_item_id,
            family_id=ctx.family_id,
            user_id=child_id_resolved,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WishListTargetResponse(
        p_active=cents_to_yuan(result["p_active"]),
        active_target_item_id=result["wish_list"].active_target_item_id,
    )


@router.delete("/wishlist/declare-target", response_model=WishListTargetResponse)
async def clear_target_endpoint(
    child_id_resolved: ChildId,
    ctx: FamilyContext,
    db: AsyncSession = Depends(get_db),
):
    """Clear the active target. P_active reverts to max_price. §4.3"""
    try:
        result = await clear_target(
            db,
            family_id=ctx.family_id,
            user_id=child_id_resolved,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WishListTargetResponse(
        p_active=cents_to_yuan(result["p_active"]),
        active_target_item_id=None,
    )
