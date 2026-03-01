"""Income API endpoint: POST /income."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import FamilyContext
from app.database import get_db
from app.models.user import User
from app.schemas.common import cents_to_yuan, yuan_to_cents
from app.schemas.income import IncomeBalances, IncomeRequest, IncomeResponse, IncomeSplitDetail
from app.services.income import process_income

router = APIRouter(tags=["income"])


@router.post("/income", response_model=IncomeResponse)
async def create_income(
    req: IncomeRequest,
    ctx: FamilyContext,
    db: AsyncSession = Depends(get_db),
):
    """Record income and auto-split to A/B/C accounts. §2"""
    try:
        amount_cents = yuan_to_cents(req.amount)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="收入金额必须为正数")

    # Resolve target child
    if ctx.role == "child":
        target_user_id = ctx.user_id
    else:
        # Parent must specify child_id
        if req.child_id is None:
            raise HTTPException(status_code=400, detail="请指定目标孩子 (child_id)")
        # Validate child belongs to family
        result = await db.execute(
            select(User).where(
                User.id == req.child_id,
                User.family_id == ctx.family_id,
                User.role == "child",
            )
        )
        if result.scalars().first() is None:
            raise HTTPException(status_code=404, detail="指定的孩子不存在或不属于您的家庭")
        target_user_id = req.child_id

    try:
        result = await process_income(
            db, amount_cents, req.description,
            family_id=ctx.family_id,
            user_id=target_user_id,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return IncomeResponse(
        total=req.amount,
        splits=IncomeSplitDetail(
            A=cents_to_yuan(result["splits"]["A"]),
            B=cents_to_yuan(result["splits"]["B"]),
            C=cents_to_yuan(result["splits"]["C"]),
        ),
        balances=IncomeBalances(
            A=cents_to_yuan(result["balances"]["A"]),
            B_principal=cents_to_yuan(result["balances"]["B_principal"]),
            B_interest_pool=cents_to_yuan(result["balances"]["B_interest_pool"]),
            C=cents_to_yuan(result["balances"]["C"]),
        ),
        escrow_note=result["escrow_note"],
    )
