"""A spending service: deduct from A account balance.

Charter reference: S3 (零钱宝使用)
"""

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import TransactionLog

logger = structlog.get_logger("spending")

SETTLEMENT_LOCK_NAME = "fambank_settlement"


async def spend_from_a(
    session: AsyncSession,
    amount_cents: int,
    description: str = "",
) -> dict:
    """Spend from A account (零钱宝).

    Args:
        session: Database session.
        amount_cents: Amount to spend in cents (must be > 0).
        description: Spending description.

    Returns:
        Dict with balance_before, balance_after, amount.

    Raises:
        ValueError: If amount <= 0 or insufficient balance (overdraft).
        RuntimeError: If settlement is in progress.
    """
    if amount_cents <= 0:
        raise ValueError("消费金额必须为正数")

    logger.info("spending_started", amount_cents=amount_cents, description=description)

    # Check that settlement is not in progress
    lock_check = await session.execute(
        text(f"SELECT IS_FREE_LOCK('{SETTLEMENT_LOCK_NAME}')")
    )
    is_free = lock_check.scalar()
    if is_free == 0:
        logger.warning("spending_blocked_by_settlement")
        raise RuntimeError("结算进行中，请稍后再试")

    # Load account A
    result = await session.execute(
        select(Account).where(Account.account_type == "A")
    )
    account_a = result.scalar_one_or_none()

    if account_a is None:
        raise RuntimeError("系统未初始化：缺少A账户")

    # Check sufficient balance
    if account_a.balance < amount_cents:
        logger.warning(
            "spending_insufficient_balance",
            balance=account_a.balance,
            requested=amount_cents,
        )
        raise ValueError(
            f"余额不足：当前余额{account_a.balance}分，"
            f"需要{amount_cents}分"
        )

    balance_before = account_a.balance
    account_a.balance -= amount_cents
    balance_after = account_a.balance

    # Create audit trail
    session.add(TransactionLog(
        type="a_spend",
        source_account="A",
        target_account=None,
        amount=amount_cents,
        balance_before=balance_before,
        balance_after=balance_after,
        charter_clause="第3条",
        description=description,
    ))

    await session.flush()

    logger.info(
        "spending_completed",
        amount_cents=amount_cents,
        balance_before=balance_before,
        balance_after=balance_after,
    )

    return {
        "balance_before": balance_before,
        "balance_after": balance_after,
        "amount": amount_cents,
    }
