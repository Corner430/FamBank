"""Accounts API: GET /accounts, spending, purchase endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyUser, ParentUser
from app.database import get_db
from app.models.account import Account
from app.models.debt import Debt
from app.schemas.common import cents_to_yuan, yuan_to_cents
from app.schemas.purchase import (
    DeductionDetail,
    PurchaseApproveRequest,
    PurchaseRequest,
    PurchaseResponse,
    RefundRequest,
    RefundResponse,
)
from app.schemas.spending import SpendRequest, SpendResponse
from app.services.purchase import execute_purchase, process_refund
from app.services.spending import spend_from_a

router = APIRouter(tags=["accounts"])


@router.get("/accounts")
async def get_accounts(
    user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    """Get all 3 account balances and details."""
    result = await db.execute(select(Account).order_by(Account.account_type))
    accounts = result.scalars().all()

    # Calculate total debt
    debt_result = await db.execute(
        select(Debt).where(Debt.remaining_amount > 0)
    )
    debts = debt_result.scalars().all()
    total_debt = sum(d.remaining_amount for d in debts)

    account_list = []
    for acc in accounts:
        entry: dict = {
            "type": acc.account_type,
            "name": acc.display_name,
        }
        if acc.account_type == "B":
            entry["principal"] = cents_to_yuan(acc.balance)
            entry["interest_pool"] = cents_to_yuan(acc.interest_pool)
            entry["is_interest_suspended"] = acc.is_interest_suspended
            entry["is_deposit_suspended"] = acc.is_deposit_suspended
        else:
            entry["balance"] = cents_to_yuan(acc.balance)

        account_list.append(entry)

    return {
        "accounts": account_list,
        "total_debt": cents_to_yuan(total_debt),
    }


@router.post("/accounts/a/spend", response_model=SpendResponse)
async def spend_a(
    req: SpendRequest,
    user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    """Spend from A account (零钱宝). §3"""
    try:
        amount_cents = yuan_to_cents(req.amount)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="消费金额必须为正数")

    try:
        result = await spend_from_a(db, amount_cents, req.description)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return SpendResponse(
        amount=req.amount,
        balance_before=cents_to_yuan(result["balance_before"]),
        balance_after=cents_to_yuan(result["balance_after"]),
    )


@router.post("/accounts/b/purchase", response_model=PurchaseResponse)
async def purchase_from_b(
    req: PurchaseRequest,
    user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    """Execute a purchase from B account (梦想金). §4.6"""
    try:
        actual_cost_cents = yuan_to_cents(req.actual_cost)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if actual_cost_cents <= 0:
        raise HTTPException(status_code=400, detail="购买金额必须为正数")

    try:
        result = await execute_purchase(
            db,
            wish_item_id=req.wish_item_id,
            actual_cost=actual_cost_cents,
            is_substitute=req.is_substitute,
            description=req.description,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PurchaseResponse(
        item_name=result["item_name"],
        actual_cost=req.actual_cost,
        deduction=DeductionDetail(
            from_principal=cents_to_yuan(result["from_principal"]),
            from_interest=cents_to_yuan(result["from_interest"]),
        ),
        b_principal_after=cents_to_yuan(result["b_principal_after"]),
        b_interest_pool_after=cents_to_yuan(result["b_interest_pool_after"]),
        transaction_ids=result["transaction_ids"],
        is_substitute=result["is_substitute"],
    )


@router.post("/accounts/b/purchase/approve", response_model=PurchaseResponse)
async def approve_substitute_purchase(
    req: PurchaseApproveRequest,
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve a substitute purchase (parent only). §4.6"""
    try:
        actual_cost_cents = yuan_to_cents(req.actual_cost)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if actual_cost_cents <= 0:
        raise HTTPException(status_code=400, detail="购买金额必须为正数")

    try:
        result = await execute_purchase(
            db,
            wish_item_id=req.wish_item_id,
            actual_cost=actual_cost_cents,
            is_substitute=True,
            description=req.description,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PurchaseResponse(
        item_name=result["item_name"],
        actual_cost=req.actual_cost,
        deduction=DeductionDetail(
            from_principal=cents_to_yuan(result["from_principal"]),
            from_interest=cents_to_yuan(result["from_interest"]),
        ),
        b_principal_after=cents_to_yuan(result["b_principal_after"]),
        b_interest_pool_after=cents_to_yuan(result["b_interest_pool_after"]),
        transaction_ids=result["transaction_ids"],
        is_substitute=True,
    )


@router.post("/accounts/b/refund", response_model=RefundResponse)
async def refund_to_b(
    req: RefundRequest,
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Process a refund back to B account. §6.2"""
    try:
        refund_cents = yuan_to_cents(req.amount)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if refund_cents <= 0:
        raise HTTPException(status_code=400, detail="退款金额必须为正数")

    try:
        result = await process_refund(
            db,
            purchase_transaction_id=req.purchase_transaction_id,
            refund_amount=refund_cents,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RefundResponse(
        refund_amount=req.amount,
        refund_to=result["refund_to"],
        b_principal_after=cents_to_yuan(result["b_principal_after"]),
        b_interest_pool_after=cents_to_yuan(result["b_interest_pool_after"]),
        transaction_id=result["transaction_id"],
    )
