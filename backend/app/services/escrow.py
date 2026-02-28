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


async def get_pending_escrow_total(session: AsyncSession) -> int:
    """Get total amount of pending (unreleased) escrow funds in cents."""
    result = await session.execute(
        select(func.coalesce(func.sum(Escrow.amount), 0)).where(
            Escrow.status == "pending"
        )
    )
    return result.scalar() or 0


async def get_escrow_summary(session: AsyncSession) -> dict:
    """Get escrow summary: pending count, pending total, released total."""
    pending = await session.execute(
        select(
            func.count(Escrow.id),
            func.coalesce(func.sum(Escrow.amount), 0),
        ).where(Escrow.status == "pending")
    )
    pending_row = pending.one()

    released = await session.execute(
        select(
            func.count(Escrow.id),
            func.coalesce(func.sum(Escrow.amount), 0),
        ).where(Escrow.status == "released")
    )
    released_row = released.one()

    summary = {
        "pending_count": pending_row[0],
        "pending_total": pending_row[1],
        "released_count": released_row[0],
        "released_total": released_row[1],
    }

    logger.info("escrow_summary_queried", **summary)

    return summary
