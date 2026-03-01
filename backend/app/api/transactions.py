"""Transactions API: GET /transactions with filters and pagination.

Charter reference: §18-19 (交易记录查询)
"""

import math
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ChildId, FamilyContext
from app.database import get_db
from app.schemas.common import cents_to_yuan
from app.schemas.transaction import TransactionItem, TransactionListResponse
from app.services.transaction import query_transactions

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    child_id_resolved: ChildId,
    ctx: FamilyContext,
    account: str | None = Query(None, description="Filter by account (A/B/C)"),
    type: str | None = Query(None, description="Filter by transaction type"),
    from_date: date | None = Query(None, description="Start date (inclusive)"),
    to_date: date | None = Query(None, description="End date (inclusive)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Query transaction log with optional filters and pagination. §18-19"""
    result = await query_transactions(
        session=db,
        account=account,
        type=type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page,
        family_id=ctx.family_id,
        user_id=child_id_resolved,
    )

    items = [
        TransactionItem(
            id=txn.id,
            timestamp=txn.timestamp,
            type=txn.type,
            source_account=txn.source_account,
            target_account=txn.target_account,
            amount=cents_to_yuan(txn.amount),
            balance_before=cents_to_yuan(txn.balance_before),
            balance_after=cents_to_yuan(txn.balance_after),
            charter_clause=txn.charter_clause,
            description=txn.description,
        )
        for txn in result["items"]
    ]

    total = result["total"]
    total_pages = max(1, math.ceil(total / per_page))

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )
