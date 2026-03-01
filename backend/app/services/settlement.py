"""4-step Settlement SOP service (charter appendix).

Steps (atomic, in order, per child):
1. C dividend -> A
2. B overflow -> C
3. B tiered interest -> B interest pool
4. Violation transfer (A -> C)

Uses MySQL advisory lock (GET_LOCK) per child to prevent concurrent income/spending.
Includes B interest suspension check (12-month timer, FR-012).
"""

from datetime import date, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.settlement import Settlement
from app.models.transaction import TransactionLog
from app.models.user import User
from app.models.violation import Violation
from app.schemas.common import cents_to_yuan
from app.services.config import apply_pending_announcements
from app.services.interest import calculate_b_interest, calculate_c_dividend
from app.services.overflow import calculate_overflow

logger = structlog.get_logger("settlement")

LOCK_TIMEOUT = 10  # seconds


async def get_p_active(
    session: AsyncSession,
    *,
    family_id: int,
    user_id: int,
) -> int:
    """Get current P_active from active wish list for a specific child.

    If no active wish list, returns 0 (no overflow constraint).
    """
    from app.models.wishlist import WishItem, WishList

    result = await session.execute(
        select(WishList).where(
            WishList.status == "active",
            WishList.family_id == family_id,
            WishList.user_id == user_id,
        )
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


async def get_config_value(
    session: AsyncSession,
    key: str,
    default: int = 0,
    *,
    family_id: int,
) -> int:
    """Get a config value as integer, scoped to family."""
    result = await session.execute(
        text(
            "SELECT value FROM config WHERE `key` = :k AND family_id = :fid "
            "ORDER BY effective_from DESC LIMIT 1"
        ),
        {"k": key, "fid": family_id},
    )
    row = result.fetchone()
    return int(row[0]) if row else default


async def execute_settlement(
    session: AsyncSession,
    settlement_date: date,
    family_id: int,
) -> dict:
    """Execute the full 4-step settlement SOP for all children in a family.

    Iterates over each child in the family and runs settlement independently.
    One child's failure does NOT abort other children.

    Returns:
        Dict with settlement_date and per-child results list.
    """
    logger.info(
        "family_settlement_started",
        settlement_date=str(settlement_date),
        family_id=family_id,
    )

    # Apply pending config announcements before settlement (family-scoped)
    applied = await apply_pending_announcements(session, settlement_date, family_id=family_id)
    if applied:
        logger.info("settlement_config_applied", count=len(applied), changes=applied)

    # Get all children in the family
    children_result = await session.execute(
        select(User).where(
            User.family_id == family_id,
            User.role == "child",
        )
    )
    children = children_result.scalars().all()

    results = []

    # Per-child try/catch: one child's failure does NOT abort others.
    # Commit happens at the API layer after this function returns, so if the
    # process crashes mid-way nothing is committed (all-or-nothing semantics).
    for child in children:
        try:
            child_result = await _execute_child_settlement(
                session=session,
                settlement_date=settlement_date,
                family_id=family_id,
                user_id=child.id,
                child_name=child.name,
            )
            results.append({
                "child_id": child.id,
                "child_name": child.name,
                "settlement_id": child_result["settlement_id"],
                "status": "completed",
                "steps": child_result["steps"],
            })
        except Exception as exc:
            logger.error(
                "child_settlement_failed",
                child_id=child.id,
                child_name=child.name,
                error=str(exc),
            )
            results.append({
                "child_id": child.id,
                "child_name": child.name,
                "settlement_id": None,
                "status": "failed",
                "steps": None,
                "error": str(exc),
            })

    logger.info(
        "family_settlement_completed",
        family_id=family_id,
        total_children=len(children),
        completed=sum(1 for r in results if r["status"] == "completed"),
        failed=sum(1 for r in results if r["status"] == "failed"),
    )

    return {
        "settlement_date": str(settlement_date),
        "results": results,
    }


async def _execute_child_settlement(
    session: AsyncSession,
    settlement_date: date,
    family_id: int,
    user_id: int,
    child_name: str | None,
) -> dict:
    """Execute the full 4-step settlement SOP for a single child.

    Acquires a per-child MySQL advisory lock to prevent concurrent writes.
    """
    lock_name = f"fambank_settlement_{user_id}"

    logger.info(
        "child_settlement_started",
        settlement_date=str(settlement_date),
        family_id=family_id,
        user_id=user_id,
        child_name=child_name,
    )

    # 1. Acquire per-child advisory lock
    lock_result = await session.execute(
        text(f"SELECT GET_LOCK('{lock_name}', {LOCK_TIMEOUT})")
    )
    lock_acquired = lock_result.scalar()
    if lock_acquired != 1:
        logger.warning("settlement_lock_failed", user_id=user_id)
        raise RuntimeError(f"无法获取结算锁 (child={user_id})，请稍后重试")

    logger.info("settlement_lock_acquired", user_id=user_id)

    try:
        # 2. Check for duplicate settlement this month for this child
        existing = await session.execute(
            select(Settlement).where(
                Settlement.family_id == family_id,
                Settlement.user_id == user_id,
                Settlement.settlement_date >= settlement_date.replace(day=1),
                Settlement.status == "completed",
            )
        )
        if existing.scalars().first():
            raise ValueError(f"本月已完成结算 (child={user_id})")

        # 3. Load accounts for this child
        result = await session.execute(
            select(Account).where(
                Account.family_id == family_id,
                Account.user_id == user_id,
            ).order_by(Account.account_type)
        )
        accounts = {a.account_type: a for a in result.scalars().all()}

        if len(accounts) < 3:
            raise RuntimeError(f"系统未初始化：缺少账户 (child={user_id})")

        account_a, account_b, account_c = accounts["A"], accounts["B"], accounts["C"]

        # Get P_active and config values (family-scoped)
        p_active = await get_p_active(session, family_id=family_id, user_id=user_id)
        c_annual_rate = await get_config_value(session, "c_annual_rate", 500, family_id=family_id)
        tier1_rate = await get_config_value(session, "b_tier1_rate", 200, family_id=family_id)
        tier1_limit = await get_config_value(session, "b_tier1_limit", 100000, family_id=family_id)
        tier2_rate = await get_config_value(session, "b_tier2_rate", 120, family_id=family_id)
        tier3_rate = await get_config_value(session, "b_tier3_rate", 30, family_id=family_id)

        # Common tenant kwargs for TransactionLog
        tx_tenant = {"family_id": family_id, "user_id": user_id}

        # Snapshot before
        snapshot_before = {
            "A": account_a.balance,
            "B_principal": account_b.balance,
            "B_interest_pool": account_b.interest_pool,
            "C": account_c.balance,
        }
        logger.info(
            "settlement_snapshot_before",
            user_id=user_id,
            **snapshot_before,
            p_active=p_active,
        )

        # Check B interest suspension (FR-012)
        await _check_b_interest_suspension(
            session, account_b, settlement_date,
            family_id=family_id, user_id=user_id,
        )

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
                **tx_tenant,
            ))

        logger.info("settlement_step1_c_dividend", user_id=user_id, amount=c_dividend)

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
                **tx_tenant,
            ))

        logger.info("settlement_step2_b_overflow", user_id=user_id, amount=b_overflow)

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
                **tx_tenant,
            ))

        logger.info(
            "settlement_step3_b_interest",
            user_id=user_id,
            total=b_interest,
            tier1=interest_result["tier1"],
            tier2=interest_result["tier2"],
            tier3=interest_result["tier3"],
            is_suspended=account_b.is_interest_suspended,
        )

        # === STEP 4: Violation transfer (A -> C) ===
        violation_transfer = await _calculate_violation_transfer(
            session, account_a, account_c, settlement_date,
            family_id=family_id, user_id=user_id,
        )

        logger.info(
            "settlement_step4_violation_transfer",
            user_id=user_id,
            amount=violation_transfer,
        )

        # Snapshot after
        snapshot_after = {
            "A": account_a.balance,
            "B_principal": account_b.balance,
            "B_interest_pool": account_b.interest_pool,
            "C": account_c.balance,
        }

        # Handle B deposit suspension auto-release
        await _check_deposit_suspension_release(
            session, account_b, settlement_date,
            family_id=family_id, user_id=user_id,
        )

        # Create settlement record
        settlement = Settlement(
            family_id=family_id,
            user_id=user_id,
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
        await session.refresh(settlement)

        logger.info(
            "child_settlement_completed",
            settlement_id=settlement.id,
            user_id=user_id,
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
        # Release per-child advisory lock
        await session.execute(
            text(f"SELECT RELEASE_LOCK('{lock_name}')")
        )
        logger.info("settlement_lock_released", user_id=user_id)


async def _check_b_interest_suspension(
    session: AsyncSession,
    account_b: Account,
    settlement_date: date,
    *,
    family_id: int,
    user_id: int,
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
            select(WishList).where(
                WishList.status == "active",
                WishList.family_id == family_id,
                WishList.user_id == user_id,
            )
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
            user_id=user_id,
            last_compliant_purchase=str(ref_date),
            threshold=str(threshold),
        )


async def _calculate_violation_transfer(
    session: AsyncSession,
    account_a: Account,
    account_c: Account,
    settlement_date: date,
    *,
    family_id: int,
    user_id: int,
) -> int:
    """Step 4: Transfer violation amounts from A to C for a specific child.

    For each violation where amount_entered_a > 0, transfer min(A_balance, entered_a) to C.
    """
    # Common tenant kwargs for TransactionLog
    tx_tenant = {"family_id": family_id, "user_id": user_id}

    # Find unresolved violations this month for this child
    month_start = settlement_date.replace(day=1)
    result = await session.execute(
        select(Violation).where(
            Violation.family_id == family_id,
            Violation.user_id == user_id,
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
                family_id=family_id,
                user_id=user_id,
                original_amount=remaining,
                remaining_amount=remaining,
                reason=f"违约划转不足：{v.description}",
                violation_id=v.id,
            )
            session.add(debt)
            logger.info(
                "debt_created",
                violation_id=v.id,
                amount=remaining,
                user_id=user_id,
            )

        session.add(TransactionLog(
            type="violation_transfer",
            source_account="A",
            target_account="C",
            amount=transfer,
            balance_before=a_before,
            balance_after=account_a.balance,
            charter_clause="第7条",
            description="违约等额划转",
            **tx_tenant,
        ))

    return total_transfer


async def _check_deposit_suspension_release(
    session: AsyncSession,
    account_b: Account,
    settlement_date: date,
    *,
    family_id: int,
    user_id: int,
) -> None:
    """Auto-release B deposit suspension after one settlement cycle."""
    if not account_b.is_deposit_suspended:
        return

    if account_b.deposit_suspend_until and settlement_date >= account_b.deposit_suspend_until:
        account_b.is_deposit_suspended = False
        account_b.deposit_suspend_until = None

        logger.info("b_deposit_suspension_released", user_id=user_id)

        # Release escrowed funds for this child
        from app.models.escrow import Escrow

        result = await session.execute(
            select(Escrow).where(
                Escrow.status == "pending",
                Escrow.family_id == family_id,
                Escrow.user_id == user_id,
            )
        )
        escrows = result.scalars().all()

        total_released = 0
        for escrow in escrows:
            escrow.status = "released"
            total_released += escrow.amount

        if total_released > 0:
            b_before = account_b.balance
            account_b.balance += total_released

            logger.info(
                "escrow_released",
                total_released=total_released,
                user_id=user_id,
            )

            session.add(TransactionLog(
                type="escrow_out",
                source_account="B_escrow",
                target_account="B",
                amount=total_released,
                balance_before=b_before,
                balance_after=account_b.balance,
                charter_clause="第7条",
                description=f"暂存资金补入：{cents_to_yuan(total_released)}元",
                family_id=family_id,
                user_id=user_id,
            ))
