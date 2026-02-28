"""C Redemption service (charter S5).

Converts C balance to A balance with a 10% fee.
Uses a two-step flow: request (validate) then approve (execute).
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import TransactionLog

logger = structlog.get_logger("redemption")


def calculate_redemption_fee(
    amount_cents: int,
    c_balance: int | None = None,
) -> tuple[int, int]:
    """Calculate redemption fee and net amount.

    Args:
        amount_cents: Amount to redeem in cents (must be > 0).
        c_balance: Current C balance in cents. If provided, validates sufficiency.

    Returns:
        Tuple of (fee_cents, net_cents). fee + net == amount_cents.

    Raises:
        ValueError: If amount <= 0 or balance insufficient.
    """
    if amount_cents <= 0:
        raise ValueError("赎回金额必须为正数")

    if c_balance is not None and c_balance < amount_cents:
        raise ValueError("C账户余额不足")

    fee = amount_cents * 10 // 100  # 10% fee, integer division
    net = amount_cents - fee
    return fee, net


async def request_redemption(
    session: AsyncSession,
    amount_cents: int,
    reason: str = "",
) -> dict:
    """Validate and preview a C redemption request.

    Checks C balance is sufficient, calculates fee and net.
    Does NOT execute -- just returns pending info for parent approval.

    Returns:
        Dict with amount, fee, net, reason for the pending request.

    Raises:
        ValueError: If amount invalid or balance insufficient.
    """
    if amount_cents <= 0:
        raise ValueError("赎回金额必须为正数")

    logger.info("redemption_requested", amount_cents=amount_cents, reason=reason)

    # Load C account
    result = await session.execute(
        select(Account).where(Account.account_type == "C")
    )
    account_c = result.scalars().first()
    if not account_c:
        raise RuntimeError("系统未初始化：缺少C账户")

    if account_c.balance < amount_cents:
        raise ValueError("C账户余额不足")

    fee, net = calculate_redemption_fee(amount_cents)

    return {
        "amount": amount_cents,
        "fee": fee,
        "net": net,
        "c_balance": account_c.balance,
        "reason": reason,
        "status": "pending",
    }


async def approve_redemption(
    session: AsyncSession,
    amount_cents: int,
    approved: bool,
    reason: str = "",
) -> dict:
    """Approve or reject a pending C redemption.

    If approved:
      - Deduct amount from C
      - Record fee as c_redemption_fee transaction
      - Add net to A as c_redemption transaction
      - Create TransactionLog entries with charter_clause="第5条"

    Returns:
        Dict with result details.
    """
    if not approved:
        logger.info("redemption_rejected", amount_cents=amount_cents, reason=reason)
        return {
            "status": "rejected",
            "amount": amount_cents,
            "reason": reason,
        }

    if amount_cents <= 0:
        raise ValueError("赎回金额必须为正数")

    # Load accounts
    result = await session.execute(
        select(Account).where(Account.account_type.in_(["A", "C"]))
    )
    accounts = {a.account_type: a for a in result.scalars().all()}
    account_a = accounts.get("A")
    account_c = accounts.get("C")

    if not account_a or not account_c:
        raise RuntimeError("系统未初始化：缺少账户")

    if account_c.balance < amount_cents:
        raise ValueError("C账户余额不足")

    fee, net = calculate_redemption_fee(amount_cents)

    # Deduct full amount from C
    c_before = account_c.balance
    account_c.balance -= amount_cents

    # Record fee transaction (C -> fee, money leaves the system)
    session.add(TransactionLog(
        type="c_redemption_fee",
        source_account="C",
        target_account=None,
        amount=fee,
        balance_before=c_before,
        balance_after=account_c.balance,
        charter_clause="第5条",
        description=f"C赎回手续费：{reason}" if reason else "C赎回手续费",
    ))

    # Add net to A
    a_before = account_a.balance
    account_a.balance += net

    session.add(TransactionLog(
        type="c_redemption",
        source_account="C",
        target_account="A",
        amount=net,
        balance_before=a_before,
        balance_after=account_a.balance,
        charter_clause="第5条",
        description=f"C赎回到A：{reason}" if reason else "C赎回到A",
    ))

    await session.flush()

    logger.info(
        "redemption_approved",
        amount_cents=amount_cents,
        fee=fee,
        net=net,
        c_balance_after=account_c.balance,
        a_balance_after=account_a.balance,
    )

    return {
        "status": "approved",
        "amount": amount_cents,
        "fee": fee,
        "net": net,
        "c_balance_after": account_c.balance,
        "a_balance_after": account_a.balance,
        "reason": reason,
    }
