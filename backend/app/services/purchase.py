"""Purchase service (charter S4.6, S6.2).

Validates and executes purchases from B account, with compliance checks,
deduction order (principal first, then interest pool), and refund processing.
"""

from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import TransactionLog
from app.models.wishlist import WishItem, WishList

logger = structlog.get_logger("purchase")


def validate_purchase_compliance(
    item_price: int,
    actual_cost: int,
    is_substitute: bool,
    b_principal: int,
    b_interest_pool: int,
) -> dict:
    """Validate purchase compliance. Pure function for unit testing.

    Rules (S4.6):
    - Actual cost must be > 0
    - If substitute: actual cost <= 120% of original item price
    - Total available = b_principal + b_interest_pool
    - Actual cost <= total available (balance sufficiency)

    Args:
        item_price: The wish item's current_price in cents
        actual_cost: Actual purchase cost in cents
        is_substitute: Whether this is a substitute purchase
        b_principal: B account principal in cents
        b_interest_pool: B account interest pool in cents

    Returns:
        Dict with 'ok' (bool), 'error' (str or None), and computed values.
    """
    if actual_cost <= 0:
        return {"ok": False, "error": "购买金额必须为正数"}

    if is_substitute:
        limit = item_price * 120 // 100
        if actual_cost > limit:
            return {
                "ok": False,
                "error": f"替代品价格不能超过原物品价格的120%（上限: {limit}分）",
            }

    total_available = b_principal + b_interest_pool
    if actual_cost > total_available:
        return {
            "ok": False,
            "error": f"余额不足（可用: {total_available}分，需要: {actual_cost}分）",
        }

    return {"ok": True, "error": None}


def calculate_deduction(
    actual_cost: int,
    b_principal: int,
    b_interest_pool: int,
) -> dict[str, int]:
    """Calculate deduction split: principal first, then interest pool.

    Args:
        actual_cost: Total cost in cents
        b_principal: Available principal in cents
        b_interest_pool: Available interest pool in cents

    Returns:
        Dict with from_principal and from_interest amounts in cents.
    """
    from_principal = min(actual_cost, b_principal)
    remainder = actual_cost - from_principal
    from_interest = min(remainder, b_interest_pool)

    return {
        "from_principal": from_principal,
        "from_interest": from_interest,
    }


async def validate_purchase(
    session: AsyncSession,
    wish_item_id: int,
    actual_cost: int,
    is_substitute: bool,
) -> dict:
    """Full purchase validation with DB lookups. S4.6

    Checks:
    - Item exists and belongs to active wish list
    - Compliance (substitute limit, balance sufficiency)

    Returns:
        Dict with 'ok', 'error', 'item', 'wish_list', 'account_b', 'deduction'.
    """
    # Look up the item
    item_result = await session.execute(
        select(WishItem).where(WishItem.id == wish_item_id)
    )
    item = item_result.scalars().first()
    if item is None:
        return {"ok": False, "error": "愿望物品不存在"}

    # Check wish list is active
    wl_result = await session.execute(
        select(WishList).where(
            WishList.id == item.wish_list_id,
            WishList.status == "active",
        )
    )
    wish_list = wl_result.scalars().first()
    if wish_list is None:
        return {"ok": False, "error": "该物品的愿望清单不是活跃状态"}

    # Load B account
    acc_result = await session.execute(
        select(Account).where(Account.account_type == "B")
    )
    account_b = acc_result.scalars().first()
    if account_b is None:
        return {"ok": False, "error": "B账户不存在"}

    # Compliance check
    compliance = validate_purchase_compliance(
        item_price=item.current_price,
        actual_cost=actual_cost,
        is_substitute=is_substitute,
        b_principal=account_b.balance,
        b_interest_pool=account_b.interest_pool,
    )

    if not compliance["ok"]:
        return compliance

    deduction = calculate_deduction(
        actual_cost, account_b.balance, account_b.interest_pool
    )

    return {
        "ok": True,
        "error": None,
        "item": item,
        "wish_list": wish_list,
        "account_b": account_b,
        "deduction": deduction,
    }


async def execute_purchase(
    session: AsyncSession,
    wish_item_id: int,
    actual_cost: int,
    is_substitute: bool,
    description: str = "",
) -> dict:
    """Execute a purchase from B account. S4.6

    Deduction order: principal first, then interest pool.
    Creates transaction records, updates last_compliant_purchase_date,
    resumes B interest if it was suspended.

    Returns:
        Dict with deduction details, balances, and transaction IDs.

    Raises:
        ValueError: If validation fails.
    """
    logger.info(
        "purchase_started",
        wish_item_id=wish_item_id,
        actual_cost=actual_cost,
        is_substitute=is_substitute,
    )

    validation = await validate_purchase(session, wish_item_id, actual_cost, is_substitute)
    if not validation["ok"]:
        logger.warning("purchase_validation_failed", error=validation["error"])
        raise ValueError(validation["error"])

    item = validation["item"]
    account_b = validation["account_b"]
    deduction = validation["deduction"]

    from_principal = deduction["from_principal"]
    from_interest = deduction["from_interest"]

    tx_ids = []

    # Deduct from principal
    if from_principal > 0:
        principal_before = account_b.balance
        account_b.balance -= from_principal
        tx_principal = TransactionLog(
            type="purchase_debit_principal",
            source_account="B",
            target_account=None,
            amount=from_principal,
            balance_before=principal_before,
            balance_after=account_b.balance,
            charter_clause="§4.6",
            description=f"购买 {item.name}: {description}" if description else f"购买 {item.name}",
        )
        session.add(tx_principal)
        await session.flush()
        tx_ids.append(tx_principal.id)

    # Deduct from interest pool
    if from_interest > 0:
        interest_before = account_b.interest_pool
        account_b.interest_pool -= from_interest
        tx_interest = TransactionLog(
            type="purchase_debit_interest",
            source_account="B_interest",
            target_account=None,
            amount=from_interest,
            balance_before=interest_before,
            balance_after=account_b.interest_pool,
            charter_clause="§4.6",
            description=f"购买 {item.name} (利息池扣除): {description}"
            if description
            else f"购买 {item.name} (利息池扣除)",
        )
        session.add(tx_interest)
        await session.flush()
        tx_ids.append(tx_interest.id)

    # Update last compliant purchase date
    today = date.today()
    account_b.last_compliant_purchase_date = today

    # Resume interest if it was suspended
    if account_b.is_interest_suspended:
        account_b.is_interest_suspended = False
        logger.info("b_interest_resumed_after_purchase", wish_item_id=wish_item_id)

    await session.flush()

    logger.info(
        "purchase_completed",
        item_name=item.name,
        actual_cost=actual_cost,
        from_principal=from_principal,
        from_interest=from_interest,
        b_principal_after=account_b.balance,
        b_interest_after=account_b.interest_pool,
    )

    return {
        "item_name": item.name,
        "actual_cost": actual_cost,
        "from_principal": from_principal,
        "from_interest": from_interest,
        "b_principal_after": account_b.balance,
        "b_interest_pool_after": account_b.interest_pool,
        "transaction_ids": tx_ids,
        "is_substitute": is_substitute,
    }


async def process_refund(
    session: AsyncSession,
    purchase_transaction_id: int,
    refund_amount: int,
) -> dict:
    """Process a refund back to B account. S6.2

    Splits refund back to principal/interest per original deduction proportions.

    Args:
        purchase_transaction_id: ID of the original purchase transaction
        refund_amount: Refund amount in cents

    Returns:
        Dict with refund details and updated balances.

    Raises:
        ValueError: If transaction not found or refund amount invalid.
    """
    if refund_amount <= 0:
        raise ValueError("退款金额必须为正数")

    logger.info(
        "refund_started",
        purchase_transaction_id=purchase_transaction_id,
        refund_amount=refund_amount,
    )

    # Find the original transaction
    tx_result = await session.execute(
        select(TransactionLog).where(TransactionLog.id == purchase_transaction_id)
    )
    original_tx = tx_result.scalars().first()
    if original_tx is None:
        raise ValueError("原始交易记录不存在")

    if original_tx.type not in ("purchase_debit_principal", "purchase_debit_interest"):
        raise ValueError("该交易不是购买交易")

    if refund_amount > original_tx.amount:
        raise ValueError("退款金额不能超过原始购买金额")

    # Load B account
    acc_result = await session.execute(
        select(Account).where(Account.account_type == "B")
    )
    account_b = acc_result.scalars().first()
    if account_b is None:
        raise ValueError("B账户不存在")

    # Refund goes back to the same pool it came from
    if original_tx.type == "purchase_debit_principal":
        principal_before = account_b.balance
        account_b.balance += refund_amount
        refund_to = "principal"
        tx = TransactionLog(
            type="refund_credit_principal",
            source_account=None,
            target_account="B",
            amount=refund_amount,
            balance_before=principal_before,
            balance_after=account_b.balance,
            charter_clause="§6.2",
            description=f"退款（本金）- 关联交易#{purchase_transaction_id}",
        )
    else:
        interest_before = account_b.interest_pool
        account_b.interest_pool += refund_amount
        refund_to = "interest"
        tx = TransactionLog(
            type="refund_credit_interest",
            source_account=None,
            target_account="B_interest",
            amount=refund_amount,
            balance_before=interest_before,
            balance_after=account_b.interest_pool,
            charter_clause="§6.2",
            description=f"退款（利息池）- 关联交易#{purchase_transaction_id}",
        )

    session.add(tx)
    await session.flush()

    logger.info(
        "refund_completed",
        refund_amount=refund_amount,
        refund_to=refund_to,
        b_principal_after=account_b.balance,
        b_interest_after=account_b.interest_pool,
    )

    return {
        "refund_amount": refund_amount,
        "refund_to": refund_to,
        "b_principal_after": account_b.balance,
        "b_interest_pool_after": account_b.interest_pool,
        "transaction_id": tx.id,
    }
