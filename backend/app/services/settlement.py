"""4-step Settlement SOP service (charter appendix).

Steps (atomic, in order):
1. C dividend -> A
2. B overflow -> C
3. B tiered interest -> B interest pool
4. Violation transfer (A -> C)

Uses MySQL advisory lock (GET_LOCK) to prevent concurrent income/spending.
Includes B interest suspension check (12-month timer, FR-012).
"""

from datetime import date, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.settlement import Settlement
from app.models.transaction import TransactionLog
from app.models.violation import Violation
from app.schemas.common import cents_to_yuan
from app.services.config import apply_pending_announcements
from app.services.interest import calculate_b_interest, calculate_c_dividend
from app.services.overflow import calculate_overflow

logger = structlog.get_logger("settlement")

SETTLEMENT_LOCK_NAME = "fambank_settlement"
LOCK_TIMEOUT = 10  # seconds


async def get_p_active(session: AsyncSession) -> int:
    """Get current P_active from active wish list.

    If no active wish list, returns 0 (no overflow constraint).
    """
    from app.models.wishlist import WishItem, WishList

    result = await session.execute(
        select(WishList).where(WishList.status == "active")
    )
    wish_list = result.scalars().first()

    if not wish_list:
        return 0

    if wish_list.active_target_item_id:
        item_result = await session.execute(
            select(WishItem).where(WishItem.id == wish_list.active_target_item_id)
        )
        item = item_result.scalars().first()
        if item:
            return item.current_price

    return wish_list.max_price


async def get_config_value(session: AsyncSession, key: str, default: int = 0) -> int:
    """Get a config value as integer."""
    result = await session.execute(
        text("SELECT value FROM config WHERE `key` = :k ORDER BY effective_from DESC LIMIT 1"),
        {"k": key},
    )
    row = result.fetchone()
    return int(row[0]) if row else default


async def execute_settlement(
    session: AsyncSession,
    settlement_date: date,
) -> dict:
    """Execute the full 4-step settlement SOP atomically.

    Acquires MySQL advisory lock to prevent concurrent writes.
    """
    logger.info("settlement_started", settlement_date=str(settlement_date))

    # 1. Acquire advisory lock
    lock_result = await session.execute(
        text(f"SELECT GET_LOCK('{SETTLEMENT_LOCK_NAME}', {LOCK_TIMEOUT})")
    )
    lock_acquired = lock_result.scalar()
    if lock_acquired != 1:
        logger.warning("settlement_lock_failed")
        raise RuntimeError("无法获取结算锁，请稍后重试")

    logger.info("settlement_lock_acquired")

    try:
        # 2. Check for duplicate settlement this month
        existing = await session.execute(
            select(Settlement).where(
                Settlement.settlement_date >= settlement_date.replace(day=1),
                Settlement.status == "completed",
            )
        )
        if existing.scalars().first():
            raise ValueError("本月已完成结算")

        # Apply pending config announcements before settlement
        applied = await apply_pending_announcements(session, settlement_date)
        if applied:
            logger.info("settlement_config_applied", count=len(applied), changes=applied)

        # 3. Load accounts
        result = await session.execute(select(Account).order_by(Account.account_type))
        accounts = {a.account_type: a for a in result.scalars().all()}
        account_a, account_b, account_c = accounts["A"], accounts["B"], accounts["C"]

        # Get P_active and config values
        p_active = await get_p_active(session)
        c_annual_rate = await get_config_value(session, "c_annual_rate", 500)
        tier1_rate = await get_config_value(session, "b_tier1_rate", 200)
        tier1_limit = await get_config_value(session, "b_tier1_limit", 100000)
        tier2_rate = await get_config_value(session, "b_tier2_rate", 120)
        tier3_rate = await get_config_value(session, "b_tier3_rate", 30)

        # Snapshot before
        snapshot_before = {
            "A": account_a.balance,
            "B_principal": account_b.balance,
            "B_interest_pool": account_b.interest_pool,
            "C": account_c.balance,
        }
        logger.info("settlement_snapshot_before", **snapshot_before, p_active=p_active)

        # Check B interest suspension (FR-012)
        await _check_b_interest_suspension(session, account_b, settlement_date)

        # === STEP 1: C dividend -> A ===
        c_dividend = calculate_c_dividend(account_c.balance, c_annual_rate)
        if c_dividend > 0:
            a_before = account_a.balance
            account_c.balance -= c_dividend
            account_a.balance += c_dividend

            session.add(TransactionLog(
                type="c_dividend",
                source_account="C",
                target_account="A",
                amount=c_dividend,
                balance_before=a_before,
                balance_after=account_a.balance,
                charter_clause="第5条",
                description=f"C派息：{cents_to_yuan(c_dividend)}元",
            ))

        logger.info("settlement_step1_c_dividend", amount=c_dividend)

        # === STEP 2: B overflow -> C ===
        overflow_result = calculate_overflow(account_b.balance, p_active)
        b_overflow = overflow_result["overflow_amount"]
        if b_overflow > 0:
            b_before = account_b.balance
            account_b.balance -= b_overflow
            account_c.balance += b_overflow

            session.add(TransactionLog(
                type="b_overflow",
                source_account="B",
                target_account="C",
                amount=b_overflow,
                balance_before=b_before,
                balance_after=account_b.balance,
                charter_clause="第4条",
                description=f"B溢出：{cents_to_yuan(b_overflow)}元",
            ))

        logger.info("settlement_step2_b_overflow", amount=b_overflow)

        # === STEP 3: B tiered interest -> B interest pool ===
        interest_result = calculate_b_interest(
            b_principal=account_b.balance,
            p_active=p_active,
            tier1_rate=tier1_rate,
            tier1_limit=tier1_limit,
            tier2_rate=tier2_rate,
            tier3_rate=tier3_rate,
            is_suspended=account_b.is_interest_suspended,
        )
        b_interest = interest_result["total"]
        if b_interest > 0:
            pool_before = account_b.interest_pool
            account_b.interest_pool += b_interest

            session.add(TransactionLog(
                type="b_interest",
                source_account=None,
                target_account="B",
                amount=b_interest,
                balance_before=pool_before,
                balance_after=account_b.interest_pool,
                charter_clause="第4条",
                description=(
                    f"B计息：T1={cents_to_yuan(interest_result['tier1'])},"
                    f"T2={cents_to_yuan(interest_result['tier2'])},"
                    f"T3={cents_to_yuan(interest_result['tier3'])}"
                ),
            ))

        logger.info(
            "settlement_step3_b_interest",
            total=b_interest,
            tier1=interest_result["tier1"],
            tier2=interest_result["tier2"],
            tier3=interest_result["tier3"],
            is_suspended=account_b.is_interest_suspended,
        )

        # === STEP 4: Violation transfer (A -> C) ===
        violation_transfer = await _calculate_violation_transfer(
            session, account_a, account_c, settlement_date
        )

        logger.info("settlement_step4_violation_transfer", amount=violation_transfer)

        # Snapshot after
        snapshot_after = {
            "A": account_a.balance,
            "B_principal": account_b.balance,
            "B_interest_pool": account_b.interest_pool,
            "C": account_c.balance,
        }

        # Handle B deposit suspension auto-release
        await _check_deposit_suspension_release(session, account_b, settlement_date)

        # Create settlement record
        settlement = Settlement(
            settlement_date=settlement_date,
            status="completed",
            c_dividend_amount=c_dividend,
            b_overflow_amount=b_overflow,
            b_interest_amount=b_interest,
            violation_transfer_amount=violation_transfer,
            p_active_at_settlement=p_active,
            snapshot_before=snapshot_before,
            snapshot_after=snapshot_after,
        )
        session.add(settlement)
        await session.flush()

        logger.info(
            "settlement_completed",
            settlement_id=settlement.id,
            **snapshot_after,
        )

        return {
            "settlement_id": settlement.id,
            "date": str(settlement_date),
            "steps": {
                "c_dividend": {"amount": c_dividend},
                "b_overflow": {"amount": b_overflow},
                "b_interest": {
                    "amount": b_interest,
                    "tier1": interest_result["tier1"],
                    "tier2": interest_result["tier2"],
                    "tier3": interest_result["tier3"],
                },
                "violation_transfer": {"amount": violation_transfer},
            },
            "balances_after": snapshot_after,
            "p_active": p_active,
        }

    finally:
        # Release advisory lock
        await session.execute(
            text(f"SELECT RELEASE_LOCK('{SETTLEMENT_LOCK_NAME}')")
        )
        logger.info("settlement_lock_released")


async def _check_b_interest_suspension(
    session: AsyncSession,
    account_b: Account,
    settlement_date: date,
) -> None:
    """Check if B should be suspended due to 12 months without compliant purchase.

    FR-012: If last_compliant_purchase_date + 12 months < settlement_date -> suspend.
    Also lifted if a new wish list is registered.
    """
    if account_b.is_interest_suspended:
        return  # Already suspended

    if account_b.last_compliant_purchase_date is None:
        # Check wish list registration date as alternative
        from app.models.wishlist import WishList

        result = await session.execute(
            select(WishList).where(WishList.status == "active")
        )
        wish_list = result.scalars().first()
        if wish_list:
            ref_date = wish_list.registered_at
        else:
            return  # No wish list, no suspension check

    else:
        ref_date = account_b.last_compliant_purchase_date

    suspend_months = 12
    threshold = ref_date + timedelta(days=suspend_months * 30)

    if settlement_date > threshold:
        account_b.is_interest_suspended = True
        logger.warning(
            "b_interest_suspended",
            last_compliant_purchase=str(ref_date),
            threshold=str(threshold),
        )


async def _calculate_violation_transfer(
    session: AsyncSession,
    account_a: Account,
    account_c: Account,
    settlement_date: date,
) -> int:
    """Step 4: Transfer violation amounts from A to C.

    For each violation where amount_entered_a > 0, transfer min(A_balance, entered_a) to C.
    """
    # Find unresolved violations this month
    month_start = settlement_date.replace(day=1)
    result = await session.execute(
        select(Violation).where(
            Violation.violation_date >= month_start,
            Violation.amount_entered_a > 0,
        )
    )
    violations = result.scalars().all()

    total_transfer = 0

    for v in violations:
        if account_a.balance <= 0:
            break

        transfer = min(account_a.balance, v.amount_entered_a)
        a_before = account_a.balance

        account_a.balance -= transfer
        account_c.balance += transfer
        total_transfer += transfer

        # Check if remaining becomes debt
        remaining = v.amount_entered_a - transfer
        if remaining > 0:
            from app.models.debt import Debt

            debt = Debt(
                original_amount=remaining,
                remaining_amount=remaining,
                reason=f"违约划转不足：{v.description}",
                violation_id=v.id,
            )
            session.add(debt)
            logger.info("debt_created", violation_id=v.id, amount=remaining)

        session.add(TransactionLog(
            type="violation_transfer",
            source_account="A",
            target_account="C",
            amount=transfer,
            balance_before=a_before,
            balance_after=account_a.balance,
            charter_clause="第7条",
            description="违约等额划转",
        ))

    return total_transfer


async def _check_deposit_suspension_release(
    session: AsyncSession,
    account_b: Account,
    settlement_date: date,
) -> None:
    """Auto-release B deposit suspension after one settlement cycle."""
    if not account_b.is_deposit_suspended:
        return

    if account_b.deposit_suspend_until and settlement_date >= account_b.deposit_suspend_until:
        account_b.is_deposit_suspended = False
        account_b.deposit_suspend_until = None

        logger.info("b_deposit_suspension_released")

        # Release escrowed funds
        from app.models.escrow import Escrow

        result = await session.execute(
            select(Escrow).where(Escrow.status == "pending")
        )
        escrows = result.scalars().all()

        total_released = 0
        for escrow in escrows:
            escrow.status = "released"
            total_released += escrow.amount

        if total_released > 0:
            b_before = account_b.balance
            account_b.balance += total_released

            logger.info("escrow_released", total_released=total_released)

            session.add(TransactionLog(
                type="escrow_out",
                source_account="B_escrow",
                target_account="B",
                amount=total_released,
                balance_before=b_before,
                balance_after=account_b.balance,
                charter_clause="第7条",
                description=f"暂存资金补入：{cents_to_yuan(total_released)}元",
            ))
