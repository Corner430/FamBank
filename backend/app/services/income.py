"""Income split logic (charter S2).

Splits income into A/B/C accounts by configured ratios.
Tail-diff (remainder from integer division) goes to C (largest ratio account).
"""

from decimal import ROUND_DOWN, Decimal

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import TransactionLog

logger = structlog.get_logger("income")

SETTLEMENT_LOCK_NAME = "fambank_settlement"


def calculate_split(
    amount_cents: int,
    ratio_a: int,
    ratio_b: int,
    ratio_c: int,
) -> dict[str, int]:
    """Calculate income split amounts in cents.

    Args:
        amount_cents: Total income in cents (must be > 0)
        ratio_a/b/c: Integer percentage for each account (must sum to 100)

    Returns:
        Dict with keys A, B, C and integer cent values.
        Tail-diff (remainder) is added to C.
    """
    if amount_cents <= 0:
        raise ValueError("收入金额必须为正数")

    if ratio_a + ratio_b + ratio_c != 100:
        raise ValueError(f"分流比例之和必须为100，当前为{ratio_a + ratio_b + ratio_c}")

    # Use Decimal for precise division, then floor to int
    total = Decimal(amount_cents)
    a_amount = int((total * ratio_a / 100).to_integral_value(rounding=ROUND_DOWN))
    b_amount = int((total * ratio_b / 100).to_integral_value(rounding=ROUND_DOWN))
    # C gets the remainder to ensure fund conservation
    c_amount = amount_cents - a_amount - b_amount

    return {"A": a_amount, "B": b_amount, "C": c_amount}


async def get_config_ratios(
    session: AsyncSession,
    *,
    family_id: int | None = None,
) -> tuple[int, int, int]:
    """Get current split ratios from config table.

    Args:
        session: Database session.
        family_id: If provided, filter config by family_id for tenant isolation.
    """
    if family_id is not None:
        result = await session.execute(
            text("SELECT `key`, value FROM config WHERE `key` IN "
                 "('split_ratio_a', 'split_ratio_b', 'split_ratio_c') "
                 "AND family_id = :family_id "
                 "ORDER BY effective_from DESC"),
            {"family_id": family_id},
        )
    else:
        result = await session.execute(
            text("SELECT `key`, value FROM config WHERE `key` IN "
                 "('split_ratio_a', 'split_ratio_b', 'split_ratio_c') "
                 "ORDER BY effective_from DESC")
        )
    rows = result.fetchall()

    ratios = {}
    for key, value in rows:
        if key not in ratios:  # Take the latest effective value
            ratios[key] = int(value)

    return (
        ratios.get("split_ratio_a", 15),
        ratios.get("split_ratio_b", 30),
        ratios.get("split_ratio_c", 55),
    )


async def process_income(
    session: AsyncSession,
    amount_cents: int,
    description: str = "",
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Process an income entry: split and update account balances.

    Args:
        session: Database session.
        amount_cents: Amount in cents (must be > 0).
        description: Income description.
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: Acting user ID for audit trail.

    Returns dict with splits, balances, and escrow_note.
    """
    if amount_cents <= 0:
        raise ValueError("收入金额必须为正数")

    logger.info(
        "income_processing_started",
        amount_cents=amount_cents,
        description=description,
        family_id=family_id,
        user_id=user_id,
    )

    # Check that settlement is not in progress
    lock_check = await session.execute(
        text("SELECT IS_FREE_LOCK(:lock_name)"),
        {"lock_name": SETTLEMENT_LOCK_NAME},
    )
    is_free = lock_check.scalar()
    if is_free == 0:
        logger.warning("income_blocked_by_settlement")
        raise RuntimeError("结算进行中，请稍后再试")

    ratio_a, ratio_b, ratio_c = await get_config_ratios(session, family_id=family_id)
    splits = calculate_split(amount_cents, ratio_a, ratio_b, ratio_c)

    logger.info(
        "income_split_calculated",
        amount_cents=amount_cents,
        ratio_a=ratio_a,
        ratio_b=ratio_b,
        ratio_c=ratio_c,
        split_a=splits["A"],
        split_b=splits["B"],
        split_c=splits["C"],
    )

    # Load accounts -- filter by family_id if provided
    stmt = select(Account).order_by(Account.account_type)
    if family_id is not None:
        stmt = stmt.where(Account.family_id == family_id)
    if user_id is not None:
        stmt = stmt.where(Account.user_id == user_id)
    result = await session.execute(stmt)
    accounts = {a.account_type: a for a in result.scalars().all()}

    if len(accounts) != 3:
        raise RuntimeError("系统未初始化：缺少账户")

    # Common kwargs for TransactionLog tenant fields
    tx_tenant = {}
    if family_id is not None:
        tx_tenant["family_id"] = family_id
    if user_id is not None:
        tx_tenant["user_id"] = user_id

    escrow_note = None

    # Check if B is deposit-suspended -> divert B portion to escrow
    account_b = accounts["B"]
    b_amount = splits["B"]

    if account_b.is_deposit_suspended and b_amount > 0:
        # Import here to avoid circular deps
        from app.models.escrow import Escrow

        escrow_kwargs: dict = {"amount": b_amount, "status": "pending"}
        if family_id is not None:
            escrow_kwargs["family_id"] = family_id
        if user_id is not None:
            escrow_kwargs["user_id"] = user_id
        escrow = Escrow(**escrow_kwargs)
        session.add(escrow)
        escrow_note = f"B账户暂停入金，{b_amount}分已暂存"

        logger.info("income_b_escrowed", amount=b_amount)

        # Record escrow transaction
        session.add(TransactionLog(
            type="escrow_in",
            source_account="external",
            target_account="B_escrow",
            amount=b_amount,
            balance_before=account_b.balance,
            balance_after=account_b.balance,
            charter_clause="第7条",
            description=f"暂存入金：{description}",
            **tx_tenant,
        ))
        # B balance doesn't change when escrowed
        b_amount = 0

    # Update A balance
    account_a = accounts["A"]
    a_before = account_a.balance

    # Check for outstanding debt -- A portion goes to debt repayment first
    a_credit = splits["A"]
    debt_repaid = await _repay_debt(
        session, account_a, a_credit, description,
        family_id=family_id, user_id=user_id,
    )
    a_credit_after_debt = a_credit - debt_repaid

    account_a.balance += a_credit_after_debt
    session.add(TransactionLog(
        type="income_split_a",
        source_account="external",
        target_account="A",
        amount=splits["A"],
        balance_before=a_before,
        balance_after=account_a.balance,
        charter_clause="第2条",
        description=description,
        **tx_tenant,
    ))

    # Update B balance (if not escrowed)
    if b_amount > 0:
        b_before = account_b.balance
        account_b.balance += b_amount
        session.add(TransactionLog(
            type="income_split_b",
            source_account="external",
            target_account="B",
            amount=b_amount,
            balance_before=b_before,
            balance_after=account_b.balance,
            charter_clause="第2条",
            description=description,
            **tx_tenant,
        ))

    # Update C balance
    account_c = accounts["C"]
    c_before = account_c.balance
    account_c.balance += splits["C"]
    session.add(TransactionLog(
        type="income_split_c",
        source_account="external",
        target_account="C",
        amount=splits["C"],
        balance_before=c_before,
        balance_after=account_c.balance,
        charter_clause="第2条",
        description=description,
        **tx_tenant,
    ))

    await session.flush()

    logger.info(
        "income_processing_completed",
        amount_cents=amount_cents,
        a_balance=account_a.balance,
        b_balance=account_b.balance,
        c_balance=account_c.balance,
        debt_repaid=debt_repaid,
    )

    return {
        "splits": {
            "A": splits["A"],
            "B": splits["B"],
            "C": splits["C"],
        },
        "balances": {
            "A": account_a.balance,
            "B_principal": account_b.balance,
            "B_interest_pool": account_b.interest_pool,
            "C": account_c.balance,
        },
        "escrow_note": escrow_note,
    }


async def _repay_debt(
    session: AsyncSession,
    account_a: Account,
    a_credit_cents: int,
    description: str,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> int:
    """Check for outstanding debts and repay from A income portion.

    Returns the amount repaid in cents.
    """
    from app.models.debt import Debt

    stmt = select(Debt).where(Debt.remaining_amount > 0).order_by(Debt.created_at)
    if family_id is not None:
        stmt = stmt.where(Debt.family_id == family_id)
    result = await session.execute(stmt)
    debts = result.scalars().all()

    if not debts:
        return 0

    # Common kwargs for TransactionLog tenant fields
    tx_tenant = {}
    if family_id is not None:
        tx_tenant["family_id"] = family_id
    if user_id is not None:
        tx_tenant["user_id"] = user_id

    total_repaid = 0
    remaining_credit = a_credit_cents

    for debt in debts:
        if remaining_credit <= 0:
            break

        repay = min(remaining_credit, debt.remaining_amount)
        debt.remaining_amount -= repay
        remaining_credit -= repay
        total_repaid += repay

        logger.info(
            "debt_repayment", debt_id=debt.id, repay_amount=repay,
            remaining=debt.remaining_amount,
        )

        session.add(TransactionLog(
            type="debt_repayment",
            source_account="A",
            target_account="C",
            amount=repay,
            balance_before=account_a.balance,
            balance_after=account_a.balance,  # A doesn't receive this portion
            charter_clause="第7条",
            description=f"偿还欠款：{description}",
            **tx_tenant,
        ))

    return total_repaid
