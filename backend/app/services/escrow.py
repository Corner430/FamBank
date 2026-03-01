"""Escrow service: buffer B portion during deposit suspension, release on resume.

The core escrow logic is integrated directly into:
- app.services.income.process_income(): Creates escrow records when B is suspended
- app.services.settlement._check_deposit_suspension_release(): Releases pending escrows

This module provides query helpers for escrow state.
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.escrow import Escrow

logger = structlog.get_logger("escrow")


async def get_pending_escrow_total(
    session: AsyncSession,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> int:
    """Get total amount of pending (unreleased) escrow funds in cents.

    Args:
        session: Database session.
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child filtering.
    """
    stmt = select(func.coalesce(func.sum(Escrow.amount), 0)).where(
        Escrow.status == "pending"
    )
    if family_id is not None:
        stmt = stmt.where(Escrow.family_id == family_id)
    if user_id is not None:
        stmt = stmt.where(Escrow.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_escrow_summary(
    session: AsyncSession,
    *,
    family_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Get escrow summary: pending count, pending total, released total.

    Args:
        session: Database session.
        family_id: Tenant family ID for multi-tenant isolation.
        user_id: User ID for per-child filtering.
    """
    pending_stmt = select(
        func.count(Escrow.id),
        func.coalesce(func.sum(Escrow.amount), 0),
    ).where(Escrow.status == "pending")
    if family_id is not None:
        pending_stmt = pending_stmt.where(Escrow.family_id == family_id)
    if user_id is not None:
        pending_stmt = pending_stmt.where(Escrow.user_id == user_id)
    pending = await session.execute(pending_stmt)
    pending_row = pending.one()

    released_stmt = select(
        func.count(Escrow.id),
        func.coalesce(func.sum(Escrow.amount), 0),
    ).where(Escrow.status == "released")
    if family_id is not None:
        released_stmt = released_stmt.where(Escrow.family_id == family_id)
    if user_id is not None:
        released_stmt = released_stmt.where(Escrow.user_id == user_id)
    released = await session.execute(released_stmt)
    released_row = released.one()

    summary = {
        "pending_count": pending_row[0],
        "pending_total": pending_row[1],
        "released_count": released_row[0],
        "released_total": released_row[1],
    }

    logger.info("escrow_summary_queried", **summary)

    return summary
