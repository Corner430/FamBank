"""WishList service (charter S4.2, S4.3).

Manages wish lists: creation with lock/valid periods, price updates,
target declaration (P_active switching).
"""

import calendar
from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wishlist import WishItem, WishList

logger = structlog.get_logger("wishlist")


def _add_months(d: date, months: int) -> date:
    """Add months to a date, clamping day to last day of target month."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calculate_wish_list_stats(items: list[dict]) -> dict[str, int]:
    """Calculate avg_price and max_price from a list of item dicts.

    Each dict must have a 'price' key (int cents).

    Returns:
        Dict with avg_price and max_price in cents.
    """
    if not items:
        raise ValueError("愿望清单不能为空")

    prices = [item["price"] for item in items]
    max_price = max(prices)
    avg_price = sum(prices) // len(prices)

    return {"avg_price": avg_price, "max_price": max_price}


def get_p_active(wish_list: WishList, items: list[WishItem]) -> int:
    """Determine P_active for a wish list.

    If active_target_item_id is set, P_active = that item's current_price.
    Otherwise, P_active = max_price of the wish list.

    Returns:
        P_active in cents.
    """
    if wish_list.active_target_item_id is not None:
        for item in items:
            if item.id == wish_list.active_target_item_id:
                return item.current_price
    return wish_list.max_price


async def get_active_wish_list(
    session: AsyncSession,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> dict | None:
    """Return the current active wish list with items, or None.

    Args:
        session: Database session.
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child wish list filtering.

    Returns:
        Dict with wish_list, items, and p_active, or None.
    """
    stmt = select(WishList).where(WishList.status == "active")
    if family_id is not None:
        stmt = stmt.where(WishList.family_id == family_id)
    if user_id is not None:
        stmt = stmt.where(WishList.user_id == user_id)
    result = await session.execute(stmt)
    wish_list = result.scalars().first()
    if wish_list is None:
        return None

    items_result = await session.execute(
        select(WishItem).where(WishItem.wish_list_id == wish_list.id)
    )
    items = list(items_result.scalars().all())

    p_active = get_p_active(wish_list, items)

    return {
        "wish_list": wish_list,
        "items": items,
        "p_active": p_active,
    }


async def create_wish_list(
    session: AsyncSession,
    items: list[dict],
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Create a new wish list with items. S4.2

    Args:
        session: DB session
        items: List of dicts with keys: name, price (cents), verification_url (optional)
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child wish list ownership.

    Returns:
        Dict with wish_list, items, and p_active.

    Raises:
        ValueError: If items empty, or within lock period of existing list.
    """
    if not items:
        raise ValueError("愿望清单不能为空")

    today = date.today()

    logger.info(
        "wishlist_creating",
        item_count=len(items),
        family_id=family_id,
        user_id=user_id,
    )

    # Check existing active list -- scoped to family + user
    existing_stmt = select(WishList).where(WishList.status == "active")
    if family_id is not None:
        existing_stmt = existing_stmt.where(WishList.family_id == family_id)
    if user_id is not None:
        existing_stmt = existing_stmt.where(WishList.user_id == user_id)
    existing = await session.execute(existing_stmt)
    existing_list = existing.scalars().first()

    if existing_list is not None:
        if today < existing_list.lock_until:
            raise ValueError(
                f"当前清单处于锁定期，{existing_list.lock_until.isoformat()} 之后才能替换"
            )
        # Mark old list as replaced
        existing_list.status = "replaced"
        logger.info("wishlist_replaced", old_id=existing_list.id)

    stats = calculate_wish_list_stats(items)

    registered_at = today
    lock_until = _add_months(registered_at, 3)
    valid_until = _add_months(registered_at, 12)

    wl_kwargs: dict = {
        "status": "active",
        "registered_at": registered_at,
        "lock_until": lock_until,
        "avg_price": stats["avg_price"],
        "max_price": stats["max_price"],
        "active_target_item_id": None,
        "valid_until": valid_until,
    }
    if family_id is not None:
        wl_kwargs["family_id"] = family_id
    if user_id is not None:
        wl_kwargs["user_id"] = user_id
    wish_list = WishList(**wl_kwargs)
    session.add(wish_list)
    await session.flush()  # Get wish_list.id

    created_items = []
    for item_data in items:
        item = WishItem(
            wish_list_id=wish_list.id,
            name=item_data["name"],
            registered_price=item_data["price"],
            current_price=item_data["price"],
            last_price_update=None,
            verification_url=item_data.get("verification_url"),
        )
        session.add(item)
        created_items.append(item)

    await session.flush()

    p_active = get_p_active(wish_list, created_items)

    logger.info(
        "wishlist_created",
        wish_list_id=wish_list.id,
        item_count=len(created_items),
        max_price=stats["max_price"],
        p_active=p_active,
    )

    return {
        "wish_list": wish_list,
        "items": created_items,
        "p_active": p_active,
    }


async def update_item_price(
    session: AsyncSession,
    item_id: int,
    new_price: int,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> WishItem:
    """Update an item's price. Limited to once per month per item. S4.2

    Args:
        item_id: Wish item ID
        new_price: New price in cents (must be > 0)
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child validation.

    Returns:
        Updated WishItem.

    Raises:
        ValueError: If item not found, list not active, price update too soon, or price <= 0.
    """
    if new_price <= 0:
        raise ValueError("价格必须为正数")

    result = await session.execute(
        select(WishItem).where(WishItem.id == item_id)
    )
    item = result.scalars().first()
    if item is None:
        raise ValueError("愿望物品不存在")

    # Check that the wish list is active and belongs to the correct family/user
    wl_stmt = select(WishList).where(WishList.id == item.wish_list_id)
    if family_id is not None:
        wl_stmt = wl_stmt.where(WishList.family_id == family_id)
    if user_id is not None:
        wl_stmt = wl_stmt.where(WishList.user_id == user_id)
    wl_result = await session.execute(wl_stmt)
    wish_list = wl_result.scalars().first()
    if wish_list is None or wish_list.status != "active":
        raise ValueError("愿望清单不是活跃状态")

    today = date.today()

    # Check once-per-month limit
    if item.last_price_update is not None:
        next_allowed = _add_months(item.last_price_update, 1)
        if today < next_allowed:
            raise ValueError(
                f"每件物品每月只能更新一次价格，下次可更新日期: {next_allowed.isoformat()}"
            )

    old_price = item.current_price
    item.current_price = new_price
    item.last_price_update = today

    # Recalculate max_price for the wish list
    items_result = await session.execute(
        select(WishItem).where(WishItem.wish_list_id == wish_list.id)
    )
    all_items = list(items_result.scalars().all())
    wish_list.max_price = max(i.current_price for i in all_items)

    # Recalculate avg_price
    wish_list.avg_price = sum(i.current_price for i in all_items) // len(all_items)

    await session.flush()

    logger.info(
        "wishlist_price_updated",
        item_id=item_id,
        old_price=old_price,
        new_price=new_price,
    )

    return item


async def declare_target(
    session: AsyncSession,
    wish_item_id: int,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Declare an item as the active target. S4.3

    Sets active_target_item_id on the active wish list.
    P_active becomes that item's current_price.

    Args:
        session: Database session.
        wish_item_id: ID of the wish item to target.
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child validation.

    Returns:
        Dict with wish_list and p_active.

    Raises:
        ValueError: If no active list, or item not in the active list.
    """
    stmt = select(WishList).where(WishList.status == "active")
    if family_id is not None:
        stmt = stmt.where(WishList.family_id == family_id)
    if user_id is not None:
        stmt = stmt.where(WishList.user_id == user_id)
    result = await session.execute(stmt)
    wish_list = result.scalars().first()
    if wish_list is None:
        raise ValueError("没有活跃的愿望清单")

    # Verify item belongs to this list
    item_result = await session.execute(
        select(WishItem).where(
            WishItem.id == wish_item_id,
            WishItem.wish_list_id == wish_list.id,
        )
    )
    item = item_result.scalars().first()
    if item is None:
        raise ValueError("该物品不在当前愿望清单中")

    wish_list.active_target_item_id = wish_item_id
    await session.flush()

    logger.info("wishlist_target_declared", item_id=wish_item_id, p_active=item.current_price)

    return {
        "wish_list": wish_list,
        "p_active": item.current_price,
    }


async def clear_target(
    session: AsyncSession,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Clear the active target. S4.3

    P_active reverts to max_price.

    Args:
        session: Database session.
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child validation.

    Returns:
        Dict with wish_list and p_active.

    Raises:
        ValueError: If no active wish list.
    """
    stmt = select(WishList).where(WishList.status == "active")
    if family_id is not None:
        stmt = stmt.where(WishList.family_id == family_id)
    if user_id is not None:
        stmt = stmt.where(WishList.user_id == user_id)
    result = await session.execute(stmt)
    wish_list = result.scalars().first()
    if wish_list is None:
        raise ValueError("没有活跃的愿望清单")

    wish_list.active_target_item_id = None
    await session.flush()

    logger.info("wishlist_target_cleared", p_active=wish_list.max_price)

    return {
        "wish_list": wish_list,
        "p_active": wish_list.max_price,
    }
