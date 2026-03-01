"""Family API endpoints: create, get, invitations, join, dashboard."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, FamilyContext, ParentContext
from app.database import get_db
from app.models.account import Account
from app.models.family import Family
from app.models.user import User
from app.schemas.common import cents_to_yuan
from app.schemas.family import (
    ChildAccountSummary,
    ChildDashboardItem,
    CreateFamilyRequest,
    CreateInvitationRequest,
    DashboardResponse,
    FamilyDetailResponse,
    FamilyInfo,
    FamilyResponse,
    InvitationInfo,
    InvitationListResponse,
    InvitationResponse,
    JoinFamilyRequest,
    JoinFamilyResponse,
    MemberInfo,
)
from app.services import family as family_service

logger = structlog.get_logger("family")

router = APIRouter(prefix="/family", tags=["family"])


@router.post("", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family(
    req: CreateFamilyRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new family. Requires logged in + no family."""
    try:
        result = await family_service.create_family(
            user_id=user["user_id"],
            name=req.name,
            db=db,
            creator_name=req.creator_name,
        )
        return FamilyResponse(
            family=FamilyInfo(**result["family"]),
            access_token=result["access_token"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("", response_model=FamilyDetailResponse)
async def get_family(
    ctx: FamilyContext,
    db: AsyncSession = Depends(get_db),
):
    """Get current family info with member list."""
    result = await family_service.get_family_detail(ctx.family_id, db)
    return FamilyDetailResponse(
        family=FamilyInfo(**result["family"]),
        members=[MemberInfo(**m) for m in result["members"]],
    )


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    req: CreateInvitationRequest,
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """Generate invitation code. Requires parent role."""
    result = await family_service.create_invitation(
        family_id=ctx.family_id,
        created_by=ctx.user_id,
        target_role=req.target_role,
        target_name=req.target_name,
        db=db,
    )
    return InvitationResponse(invitation=InvitationInfo(**result["invitation"]))


@router.get("/invitations", response_model=InvitationListResponse)
async def list_invitations(
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """List all invitations for the family. Requires parent role."""
    invitations = await family_service.list_invitations(ctx.family_id, db)
    return InvitationListResponse(
        invitations=[InvitationInfo(**inv) for inv in invitations]
    )


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: int,
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a pending invitation. Requires parent role."""
    try:
        await family_service.revoke_invitation(invitation_id, ctx.family_id, db)
        return {"message": "邀请码已撤销"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/join", response_model=JoinFamilyResponse)
async def join_family(
    req: JoinFamilyRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Join a family using an invitation code. Requires logged in + no family."""
    try:
        result = await family_service.join_family(
            user_id=user["user_id"],
            code=req.code,
            db=db,
        )
        return JoinFamilyResponse(
            family=FamilyInfo(**result["family"]),
            role=result["role"],
            name=result["name"],
            access_token=result["access_token"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """Get family dashboard with all children's account balances. Parent-only."""
    # Get family name
    fam_result = await db.execute(select(Family).where(Family.id == ctx.family_id))
    family = fam_result.scalars().first()
    if family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="家庭不存在",
        )

    # Get all children in family
    children_result = await db.execute(
        select(User).where(
            User.family_id == ctx.family_id,
            User.role == "child",
        )
    )
    children = children_result.scalars().all()

    overall_total = 0
    child_items: list[ChildDashboardItem] = []

    for child in children:
        # Get A/B/C accounts for this child
        accts_result = await db.execute(
            select(Account).where(
                Account.family_id == ctx.family_id,
                Account.user_id == child.id,
            )
        )
        accts = {a.account_type: a for a in accts_result.scalars().all()}

        a_balance = accts["A"].balance if "A" in accts else 0
        b_principal = accts["B"].balance if "B" in accts else 0
        b_interest_pool = accts["B"].interest_pool if "B" in accts else 0
        c_balance = accts["C"].balance if "C" in accts else 0

        child_total = a_balance + b_principal + b_interest_pool + c_balance
        overall_total += child_total

        child_items.append(
            ChildDashboardItem(
                user_id=child.id,
                name=child.name,
                accounts=ChildAccountSummary(
                    A=cents_to_yuan(a_balance),
                    B_principal=cents_to_yuan(b_principal),
                    B_interest_pool=cents_to_yuan(b_interest_pool),
                    C=cents_to_yuan(c_balance),
                ),
                total=cents_to_yuan(child_total),
            )
        )

    logger.info(
        "dashboard_queried",
        family_id=ctx.family_id,
        children_count=len(child_items),
        total_assets=overall_total,
    )

    return DashboardResponse(
        family_name=family.name,
        total_assets=cents_to_yuan(overall_total),
        children=child_items,
    )
