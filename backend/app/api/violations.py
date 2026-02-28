"""Violations API: POST /violations, GET /violations.

Charter reference: §7 (违约处理)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyUser, ParentUser
from app.database import get_db
from app.models.violation import Violation
from app.schemas.common import cents_to_yuan, yuan_to_cents
from app.schemas.violation import (
    ViolationItem,
    ViolationListResponse,
    ViolationRequest,
    ViolationResponse,
)
from app.services.violation import process_violation

router = APIRouter(tags=["violations"])


@router.post("/violations", response_model=ViolationResponse)
async def create_violation(
    req: ViolationRequest,
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Record and process a violation. Parent-only. §7"""
    try:
        violation_cents = yuan_to_cents(req.violation_amount)
        entered_a_cents = yuan_to_cents(req.amount_entered_a)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if violation_cents <= 0:
        raise HTTPException(status_code=400, detail="违约金额必须为正数")
    if entered_a_cents < 0:
        raise HTTPException(status_code=400, detail="进入A账户的金额不能为负数")

    try:
        result = await process_violation(
            db, violation_cents, entered_a_cents, req.description
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ViolationResponse(
        violation_id=result["violation_id"],
        penalty=cents_to_yuan(result["penalty"]),
        is_escalated=result["is_escalated"],
        b_interest_pool_before=cents_to_yuan(result["b_interest_pool_before"]),
        b_interest_pool_after=cents_to_yuan(result["b_interest_pool_after"]),
        c_balance_before=cents_to_yuan(result["c_balance_before"]),
        c_balance_after=cents_to_yuan(result["c_balance_after"]),
        deposit_suspend_until=result["deposit_suspend_until"],
    )


@router.get("/violations", response_model=ViolationListResponse)
async def list_violations(
    user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    """Get violation history. §7"""
    count_result = await db.execute(select(func.count(Violation.id)))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Violation).order_by(Violation.violation_date.desc(), Violation.id.desc())
    )
    violations = result.scalars().all()

    items = [
        ViolationItem(
            id=v.id,
            violation_date=v.violation_date,
            violation_amount=cents_to_yuan(v.violation_amount),
            penalty_amount=cents_to_yuan(v.penalty_amount),
            amount_entered_a=cents_to_yuan(v.amount_entered_a),
            is_escalated=v.is_escalated,
            description=v.description,
        )
        for v in violations
    ]

    return ViolationListResponse(items=items, total=total)
