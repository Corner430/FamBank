"""Settlement API endpoints: POST /settlement, GET /settlements."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ParentContext
from app.database import get_db
from app.models.settlement import Settlement
from app.schemas.common import cents_to_yuan
from app.schemas.settlement import (
    ChildSettlementResult,
    FamilySettlementResponse,
    SettlementInterestDetail,
    SettlementStepDetail,
    SettlementSteps,
)
from app.services.settlement import execute_settlement

router = APIRouter(tags=["settlement"])


@router.post("/settlement", response_model=FamilySettlementResponse)
async def create_settlement(
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """Trigger monthly settlement for all children in the family. Parent-only. §SOP"""
    today = date.today()

    try:
        result = await execute_settlement(db, today, family_id=ctx.family_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    child_results = []
    for r in result["results"]:
        steps = None
        if r["steps"] is not None:
            s = r["steps"]
            steps = SettlementSteps(
                c_dividend=SettlementStepDetail(
                    amount=cents_to_yuan(s["c_dividend"]["amount"]),
                ),
                b_overflow=SettlementStepDetail(
                    amount=cents_to_yuan(s["b_overflow"]["amount"]),
                ),
                b_interest=SettlementInterestDetail(
                    amount=cents_to_yuan(s["b_interest"]["amount"]),
                    tier1=cents_to_yuan(s["b_interest"]["tier1"]),
                    tier2=cents_to_yuan(s["b_interest"]["tier2"]),
                    tier3=cents_to_yuan(s["b_interest"]["tier3"]),
                ),
                violation_transfer=SettlementStepDetail(
                    amount=cents_to_yuan(s["violation_transfer"]["amount"]),
                ),
            )

        child_results.append(
            ChildSettlementResult(
                child_id=r["child_id"],
                child_name=r["child_name"],
                settlement_id=r["settlement_id"],
                status=r["status"],
                steps=steps,
                error=r.get("error"),
            )
        )

    return FamilySettlementResponse(
        settlement_date=result["settlement_date"],
        results=child_results,
    )


@router.get("/settlements")
async def list_settlements(
    ctx: ParentContext,
    page: int = 1,
    per_page: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """List settlement history for the family. Parent-only."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Settlement)
        .where(Settlement.family_id == ctx.family_id)
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
                "user_id": s.user_id,
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
