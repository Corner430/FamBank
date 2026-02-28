"""Settlement API endpoints: POST /settlement, GET /settlements."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ParentUser
from app.database import get_db
from app.models.settlement import Settlement
from app.schemas.common import cents_to_yuan
from app.schemas.settlement import (
    SettlementBalances,
    SettlementInterestDetail,
    SettlementResponse,
    SettlementStepDetail,
    SettlementSteps,
)
from app.services.settlement import execute_settlement

router = APIRouter(tags=["settlement"])


@router.post("/settlement", response_model=SettlementResponse)
async def create_settlement(
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Trigger monthly settlement. Parent-only. §SOP"""
    today = date.today()

    try:
        result = await execute_settlement(db, today)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    steps = result["steps"]
    balances = result["balances_after"]

    return SettlementResponse(
        settlement_id=result["settlement_id"],
        date=result["date"],
        steps=SettlementSteps(
            c_dividend=SettlementStepDetail(
                amount=cents_to_yuan(steps["c_dividend"]["amount"]),
            ),
            b_overflow=SettlementStepDetail(
                amount=cents_to_yuan(steps["b_overflow"]["amount"]),
            ),
            b_interest=SettlementInterestDetail(
                amount=cents_to_yuan(steps["b_interest"]["amount"]),
                tier1=cents_to_yuan(steps["b_interest"]["tier1"]),
                tier2=cents_to_yuan(steps["b_interest"]["tier2"]),
                tier3=cents_to_yuan(steps["b_interest"]["tier3"]),
            ),
            violation_transfer=SettlementStepDetail(
                amount=cents_to_yuan(steps["violation_transfer"]["amount"]),
            ),
        ),
        balances_after=SettlementBalances(
            A=cents_to_yuan(balances["A"]),
            B_principal=cents_to_yuan(balances["B_principal"]),
            B_interest_pool=cents_to_yuan(balances["B_interest_pool"]),
            C=cents_to_yuan(balances["C"]),
        ),
    )


@router.get("/settlements")
async def list_settlements(
    user: ParentUser,
    page: int = 1,
    per_page: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """List settlement history. Parent-only."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Settlement)
        .order_by(Settlement.settlement_date.desc())
        .limit(per_page)
        .offset(offset)
    )
    settlements = result.scalars().all()

    return {
        "settlements": [
            {
                "id": s.id,
                "date": str(s.settlement_date),
                "status": s.status,
                "c_dividend": cents_to_yuan(s.c_dividend_amount),
                "b_overflow": cents_to_yuan(s.b_overflow_amount),
                "b_interest": cents_to_yuan(s.b_interest_amount),
                "violation_transfer": cents_to_yuan(s.violation_transfer_amount),
            }
            for s in settlements
        ],
        "page": page,
        "per_page": per_page,
    }
