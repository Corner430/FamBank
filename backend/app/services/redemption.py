"""C Redemption service (charter S5).

Converts C balance to A balance with a 10% fee.
Uses a two-step flow: request (persist) then approve/reject (execute).
"""

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.redemption_request import RedemptionRequest
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
    user_id: int,
    reason: str = "",
    *,
    family_id: int | None = None,
) -> dict:
    """Validate and persist a C redemption request.

    Creates a RedemptionRequest record in the database with status='pending'.

    Args:
        session: Database session.
        amount_cents: Amount to redeem in cents.
        user_id: Requesting user ID.
        reason: Reason for redemption.
        family_id: Tenant family ID for multi-tenant isolation.

    Returns:
        Dict with id, amount, fee, net, c_balance, reason, status, created_at.

    Raises:
        ValueError: If amount invalid or balance insufficient.
    """
    if amount_cents <= 0:
        raise ValueError("赎回金额必须为正数")

    logger.info(
        "redemption_requested",
        amount_cents=amount_cents,
        reason=reason,
        user_id=user_id,
        family_id=family_id,
    )

    # Load C account -- filter by family_id and user_id for tenant isolation
    stmt = select(Account).where(Account.account_type == "C")
    if family_id is not None:
        stmt = stmt.where(Account.family_id == family_id)
    stmt = stmt.where(Account.user_id == user_id)
    result = await session.execute(stmt)
    account_c = result.scalars().first()
    if not account_c:
        raise RuntimeError("系统未初始化：缺少C账户")

    if account_c.balance < amount_cents:
        raise ValueError("C账户余额不足")

    fee, net = calculate_redemption_fee(amount_cents)

    record_kwargs: dict = {
        "amount": amount_cents,
        "fee": fee,
        "net": net,
        "reason": reason,
        "status": "pending",
        "requested_by": user_id,
    }
    if family_id is not None:
        record_kwargs["family_id"] = family_id
    record = RedemptionRequest(**record_kwargs)
    session.add(record)
    await session.flush()
    await session.refresh(record)

    return {
        "id": record.id,
        "amount": amount_cents,
        "fee": fee,
        "net": net,
        "c_balance": account_c.balance,
        "reason": reason,
        "status": "pending",
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


async def approve_redemption(
    session: AsyncSession,
    request_id: int,
    approved: bool,
    reviewer_id: int,
    *,
    family_id: int | None = None,
) -> dict:
    """Approve or reject a pending C redemption by record id.

    If approved:
      - Deduct amount from C
      - Record fee as c_redemption_fee transaction
      - Add net to A as c_redemption transaction
      - Create TransactionLog entries with charter_clause="第5条"

    Args:
        session: Database session.
        request_id: ID of the RedemptionRequest.
        approved: Whether to approve or reject.
        reviewer_id: Reviewing user ID.
        family_id: Tenant family ID for multi-tenant isolation.

    Returns:
        Dict with result details.
    """
    # Load the redemption request -- filter by family_id for tenant isolation
    rr_stmt = select(RedemptionRequest).where(RedemptionRequest.id == request_id)
    if family_id is not None:
        rr_stmt = rr_stmt.where(RedemptionRequest.family_id == family_id)
    result = await session.execute(rr_stmt)
    record = result.scalars().first()
    if not record:
        raise ValueError("赎回请求不存在")

    if record.status != "pending":
        raise ValueError("该赎回请求已处理")

    now = datetime.now(tz=UTC).replace(tzinfo=None)

    if not approved:
        record.status = "rejected"
        record.reviewed_by = reviewer_id
        record.reviewed_at = now
        await session.flush()

        logger.info("redemption_rejected", request_id=request_id, reviewer_id=reviewer_id)
        return {
            "id": record.id,
            "status": "rejected",
            "amount": record.amount,
            "reason": record.reason,
        }

    # Load accounts -- filter by family_id for tenant isolation
    acc_stmt = select(Account).where(Account.account_type.in_(["A", "C"]))
    if family_id is not None:
        acc_stmt = acc_stmt.where(Account.family_id == family_id)
    # Use the requesting user's accounts
    acc_stmt = acc_stmt.where(Account.user_id == record.requested_by)
    result = await session.execute(acc_stmt)
    accounts = {a.account_type: a for a in result.scalars().all()}
    account_a = accounts.get("A")
    account_c = accounts.get("C")

    if not account_a or not account_c:
        raise RuntimeError("系统未初始化：缺少账户")

    if account_c.balance < record.amount:
        raise ValueError("C账户余额不足")

    # Common kwargs for TransactionLog tenant fields
    tx_tenant = {}
    if family_id is not None:
        tx_tenant["family_id"] = family_id
    # Use the requesting user's ID for the transaction log
    tx_tenant["user_id"] = record.requested_by

    # Deduct full amount from C
    c_before = account_c.balance
    account_c.balance -= record.amount

    # Record fee transaction (C -> fee, money leaves the system)
    session.add(TransactionLog(
        type="c_redemption_fee",
        source_account="C",
        target_account=None,
        amount=record.fee,
        balance_before=c_before,
        balance_after=account_c.balance,
        charter_clause="第5条",
        description=f"C赎回手续费：{record.reason}" if record.reason else "C赎回手续费",
        **tx_tenant,
    ))

    # Add net to A
    a_before = account_a.balance
    account_a.balance += record.net

    session.add(TransactionLog(
        type="c_redemption",
        source_account="C",
        target_account="A",
        amount=record.net,
        balance_before=a_before,
        balance_after=account_a.balance,
        charter_clause="第5条",
        description=f"C赎回到A：{record.reason}" if record.reason else "C赎回到A",
        **tx_tenant,
    ))

    # Update record status
    record.status = "approved"
    record.reviewed_by = reviewer_id
    record.reviewed_at = now

    await session.flush()

    logger.info(
        "redemption_approved",
        request_id=request_id,
        amount_cents=record.amount,
        fee=record.fee,
        net=record.net,
        c_balance_after=account_c.balance,
        a_balance_after=account_a.balance,
    )

    return {
        "id": record.id,
        "status": "approved",
        "amount": record.amount,
        "fee": record.fee,
        "net": record.net,
        "c_balance_after": account_c.balance,
        "a_balance_after": account_a.balance,
        "reason": record.reason,
    }


async def get_pending_redemptions(
    session: AsyncSession,
    *,
    family_id: int | None = None,
) -> list[dict]:
    """Query all pending redemption requests.

    Args:
        session: Database session.
        family_id: Tenant family ID for multi-tenant isolation.
    """
    rr_stmt = (
        select(RedemptionRequest)
        .where(RedemptionRequest.status == "pending")
        .order_by(RedemptionRequest.created_at.asc())
    )
    if family_id is not None:
        rr_stmt = rr_stmt.where(RedemptionRequest.family_id == family_id)
    result = await session.execute(rr_stmt)
    records = result.scalars().all()

    # Also load current C balance for display -- filter by family
    c_stmt = select(Account).where(Account.account_type == "C")
    if family_id is not None:
        c_stmt = c_stmt.where(Account.family_id == family_id)
    c_result = await session.execute(c_stmt)
    account_c = c_result.scalars().first()
    c_balance = account_c.balance if account_c else 0

    return [
        {
            "id": r.id,
            "amount": r.amount,
            "fee": r.fee,
            "net": r.net,
            "c_balance": c_balance,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in records
    ]
