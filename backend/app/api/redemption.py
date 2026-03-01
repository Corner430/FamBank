"""C Redemption API endpoints: request, approve/reject, list pending. S5"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyUser, ParentUser
from app.database import get_db
from app.schemas.common import cents_to_yuan, yuan_to_cents
from app.schemas.redemption import (
    RedemptionApproveRequest,
    RedemptionPending,
    RedemptionPendingList,
    RedemptionRequest,
    RedemptionResult,
)
from app.services.redemption import (
    approve_redemption,
    get_pending_redemptions,
    request_redemption,
)

router = APIRouter(tags=["redemption"])


@router.post("/accounts/c/redemption/request", response_model=RedemptionPending)
async def create_redemption_request(
    req: RedemptionRequest,
    user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    """Request C redemption (any auth). S5"""
    try:
        amount_cents = yuan_to_cents(req.amount)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="赎回金额必须为正数")

    try:
        result = await request_redemption(db, amount_cents, user["user_id"], req.reason)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedemptionPending(
        id=result["id"],
        amount=cents_to_yuan(result["amount"]),
        fee=cents_to_yuan(result["fee"]),
        net=cents_to_yuan(result["net"]),
        c_balance=cents_to_yuan(result["c_balance"]),
        reason=result["reason"],
        status=result["status"],
        created_at=result["created_at"],
    )


@router.post("/accounts/c/redemption/approve", response_model=RedemptionResult)
async def approve_redemption_request(
    req: RedemptionApproveRequest,
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject C redemption (parent auth). S5"""
    try:
        result = await approve_redemption(db, req.id, req.approved, user["user_id"])
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result["status"] == "rejected":
        return RedemptionResult(
            id=result["id"],
            status="rejected",
            amount=cents_to_yuan(result["amount"]),
            reason=result.get("reason", ""),
        )

    return RedemptionResult(
        id=result["id"],
        status="approved",
        amount=cents_to_yuan(result["amount"]),
        fee=cents_to_yuan(result["fee"]),
        net=cents_to_yuan(result["net"]),
        c_balance_after=cents_to_yuan(result["c_balance_after"]),
        a_balance_after=cents_to_yuan(result["a_balance_after"]),
        reason=result.get("reason", ""),
    )


@router.get("/accounts/c/redemption/pending", response_model=RedemptionPendingList)
async def list_pending_redemptions(
    user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    """List all pending C redemption requests (any auth). S5"""
    rows = await get_pending_redemptions(db)
    return RedemptionPendingList(
        requests=[
            RedemptionPending(
                id=r["id"],
                amount=cents_to_yuan(r["amount"]),
                fee=cents_to_yuan(r["fee"]),
                net=cents_to_yuan(r["net"]),
                c_balance=cents_to_yuan(r["c_balance"]),
                reason=r["reason"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    )
