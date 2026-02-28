"""Violation processing service: penalties, escalation, transaction logging.

Charter reference: S7 (违约处理)
"""

from datetime import date, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import TransactionLog
from app.models.violation import Violation

logger = structlog.get_logger("violation")


async def process_violation(
    session: AsyncSession,
    violation_amount: int,
    amount_entered_a: int,
    description: str = "",
) -> dict:
    """Process a violation: calculate penalty, transfer, check escalation.

    Args:
        session: Database session.
        violation_amount: The violation amount in cents.
        amount_entered_a: How much of the violation entered A account (for settlement step 4).
        description: Violation description.

    Returns:
        Dict with violation details (penalty, escalated, balances).

    Raises:
        ValueError: If violation_amount <= 0 or amount_entered_a < 0.
    """
    if violation_amount <= 0:
        raise ValueError("违约金额必须为正数")
    if amount_entered_a < 0:
        raise ValueError("进入A账户的金额不能为负数")

    logger.info(
        "violation_processing_started",
        violation_amount=violation_amount,
        amount_entered_a=amount_entered_a,
        description=description,
    )

    # Load accounts
    result = await session.execute(
        select(Account).order_by(Account.account_type)
    )
    accounts = {a.account_type: a for a in result.scalars().all()}

    if len(accounts) < 3:
        raise RuntimeError("系统未初始化：缺少账户")

    account_b = accounts["B"]
    account_c = accounts["C"]

    # Calculate penalty: min(B_interest_pool, 2 * violation_amount)
    penalty = calculate_penalty(account_b.interest_pool, violation_amount)

    logger.info(
        "violation_penalty_calculated", penalty=penalty,
        b_interest_pool=account_b.interest_pool,
    )

    # Transfer penalty from B interest_pool to C
    b_pool_before = account_b.interest_pool
    c_before = account_c.balance

    account_b.interest_pool -= penalty
    account_c.balance += penalty

    # Log penalty transfer transactions
    if penalty > 0:
        session.add(TransactionLog(
            type="violation_penalty",
            source_account="B_interest_pool",
            target_account="C",
            amount=penalty,
            balance_before=b_pool_before,
            balance_after=account_b.interest_pool,
            charter_clause="第7条",
            description=f"违约罚金：{description}",
        ))

        session.add(TransactionLog(
            type="violation_penalty_credit",
            source_account="B_interest_pool",
            target_account="C",
            amount=penalty,
            balance_before=c_before,
            balance_after=account_c.balance,
            charter_clause="第7条",
            description=f"违约罚金入C：{description}",
        ))

    # Check escalation: 2nd violation in 12 months
    today = date.today()
    twelve_months_ago = today - timedelta(days=365)

    count_result = await session.execute(
        select(func.count(Violation.id)).where(
            Violation.violation_date >= twelve_months_ago
        )
    )
    recent_violations = count_result.scalar_one()

    # This is the new violation (not yet saved), so if recent count >= 1
    # that means this will be the 2nd (or more) in 12 months
    is_escalated = recent_violations >= 1

    if is_escalated:
        account_b.is_deposit_suspended = True
        # Calculate suspend_until: next settlement date + 1 month
        next_settlement = await _get_next_settlement_date(session, today)
        account_b.deposit_suspend_until = next_settlement + timedelta(days=30)
        logger.warning(
            "violation_escalated",
            recent_violations=recent_violations + 1,
            deposit_suspend_until=str(account_b.deposit_suspend_until),
        )

    # Create Violation record
    violation = Violation(
        violation_date=today,
        violation_amount=violation_amount,
        penalty_amount=penalty,
        amount_entered_a=amount_entered_a,
        is_escalated=is_escalated,
        description=description,
    )
    session.add(violation)

    await session.flush()

    logger.info(
        "violation_processing_completed",
        violation_id=violation.id,
        penalty=penalty,
        is_escalated=is_escalated,
    )

    return {
        "violation_id": violation.id,
        "penalty": penalty,
        "is_escalated": is_escalated,
        "b_interest_pool_before": b_pool_before,
        "b_interest_pool_after": account_b.interest_pool,
        "c_balance_before": c_before,
        "c_balance_after": account_c.balance,
        "deposit_suspend_until": (
            account_b.deposit_suspend_until.isoformat()
            if is_escalated and account_b.deposit_suspend_until
            else None
        ),
    }


def calculate_penalty(b_interest_pool: int, violation_amount: int) -> int:
    """Calculate penalty amount.

    penalty = min(B_interest_pool, 2 * violation_amount)

    Args:
        b_interest_pool: Current B interest pool balance in cents.
        violation_amount: Violation amount in cents.

    Returns:
        Penalty amount in cents.
    """
    return min(b_interest_pool, 2 * violation_amount)


async def _get_next_settlement_date(session: AsyncSession, today: date) -> date:
    """Get the next settlement date (1st of next month by default).

    If there is a settlement history, use the pattern; otherwise default
    to the 1st of the next month.
    """
    # Simple: next settlement is 1st of next month
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    else:
        return date(today.year, today.month + 1, 1)
