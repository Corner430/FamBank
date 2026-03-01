"""API dependencies: JWT auth, tenant context, role enforcement, child resolution."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.database import get_db
from app.models.user import User
from app.services.tenant import TenantContext


async def get_current_user(request: Request) -> dict:
    """Extract and validate the current user from Authorization header JWT."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
        )

    return {
        "user_id": int(payload["sub"]),
        "family_id": payload.get("family_id"),
        "role": payload.get("role"),
    }


async def get_tenant_context(user: dict = Depends(get_current_user)) -> TenantContext:
    """Build a TenantContext from the current user's JWT claims."""
    return TenantContext(
        user_id=user["user_id"],
        family_id=user.get("family_id"),
        role=user.get("role"),
    )


async def require_family(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    """Require that the user belongs to a family. Returns TenantContext."""
    ctx.require_family()
    return ctx


async def require_parent(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    """Require parent role. Returns TenantContext."""
    ctx.require_parent()
    return ctx


async def resolve_child_id(
    child_id: int | None = Query(None, description="目标孩子ID（家长必传）"),
    ctx: TenantContext = Depends(require_family),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Resolve the target child user_id.

    - Parent: must provide child_id query param; validates child belongs to family.
    - Child: uses own user_id from JWT; rejects if child_id param differs from self.
    """
    if ctx.role == "child":
        if child_id is not None and child_id != ctx.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作其他成员的数据",
            )
        return ctx.user_id

    # Parent must provide child_id
    if child_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请指定目标孩子 (child_id)",
        )

    # Validate child belongs to same family
    result = await db.execute(
        select(User).where(
            User.id == child_id,
            User.family_id == ctx.family_id,
            User.role == "child",
        )
    )
    child = result.scalars().first()
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定的孩子不存在或不属于您的家庭",
        )

    return child_id


# Type aliases for dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
FamilyContext = Annotated[TenantContext, Depends(require_family)]
ParentContext = Annotated[TenantContext, Depends(require_parent)]
ChildId = Annotated[int, Depends(resolve_child_id)]

# Backward-compatible aliases for existing API routes (will be removed after full migration).
# These return dict (not TenantContext) to match the old API contract.

async def _require_parent_dict(user: dict = Depends(get_current_user)) -> dict:
    """Require parent role; returns dict for backward compat."""
    if user.get("role") != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅甲方可执行此操作",
        )
    return user


AnyUser = CurrentUser
ParentUser = Annotated[dict, Depends(_require_parent_dict)]
