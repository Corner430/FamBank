"""Transaction query service: filtering, pagination for audit log.

Charter reference: §18-19 (交易记录查询)
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import TransactionLog


async def query_transactions(
    session: AsyncSession,
    account: str | None = None,
    type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Query transaction log with optional filters and pagination.

    Args:
        session: Database session.
        account: Filter by source_account or target_account (e.g. "A", "B", "C").
        type: Filter by transaction type (e.g. "income_split_a", "a_spend").
        from_date: Include transactions on or after this date.
        to_date: Include transactions on or before this date.
        page: Page number (1-based).
        per_page: Items per page (max 100).

    Returns:
        Dict with "items" (list of TransactionLog) and "total" (int).
    """
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    # Build base filter conditions
    conditions = []

    if account is not None:
        conditions.append(
            (TransactionLog.source_account == account)
            | (TransactionLog.target_account == account)
        )

    if type is not None:
        conditions.append(TransactionLog.type == type)

    if from_date is not None:
        conditions.append(func.date(TransactionLog.timestamp) >= from_date)

    if to_date is not None:
        conditions.append(func.date(TransactionLog.timestamp) <= to_date)

    # Count query
    count_stmt = select(func.count(TransactionLog.id))
    for cond in conditions:
        count_stmt = count_stmt.where(cond)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Data query with pagination
    offset = (page - 1) * per_page
    data_stmt = (
        select(TransactionLog)
        .order_by(TransactionLog.timestamp.desc(), TransactionLog.id.desc())
    )
    for cond in conditions:
        data_stmt = data_stmt.where(cond)
    data_stmt = data_stmt.offset(offset).limit(per_page)

    result = await session.execute(data_stmt)
    items = result.scalars().all()

    return {"items": items, "total": total}
