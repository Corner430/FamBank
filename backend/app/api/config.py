"""Config API endpoints: list config, announce changes. S8"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ParentContext
from app.database import get_db
from app.models.config import Announcement
from app.schemas.config import (
    AnnouncementDetail,
    AnnounceRequest,
    ConfigItem,
    ConfigListResponse,
)
from app.services.config import announce_change, get_all_config

router = APIRouter(tags=["config"])


@router.get("/config", response_model=ConfigListResponse)
async def list_config(
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """List all current config values for the family. Parent-only. S8"""
    configs = await get_all_config(db, family_id=ctx.family_id)
    return ConfigListResponse(
        configs=[
            ConfigItem(
                key=c["key"],
                value=c["value"],
                effective_from=c["effective_from"],
            )
            for c in configs
        ]
    )


@router.post("/config/announce", response_model=AnnouncementDetail)
async def create_announcement(
    req: AnnounceRequest,
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """Announce a config parameter change (effective next month 1st). Parent-only. S8"""
    if not req.key.strip():
        raise HTTPException(status_code=400, detail="参数名不能为空")
    if not req.new_value.strip():
        raise HTTPException(status_code=400, detail="参数值不能为空")

    try:
        result = await announce_change(
            db, req.key, req.new_value, req.reason,
            family_id=ctx.family_id,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AnnouncementDetail(
        id=result["id"],
        config_key=result["config_key"],
        old_value=result["old_value"],
        new_value=result["new_value"],
        announced_at=result["announced_at"],
        effective_from=result["effective_from"],
        reason=result.get("reason", ""),
    )


@router.get("/config/announcements")
async def list_announcements(
    ctx: ParentContext,
    db: AsyncSession = Depends(get_db),
):
    """List all announcements for the family. Parent-only. S8"""
    result = await db.execute(
        select(Announcement)
        .where(Announcement.family_id == ctx.family_id)
        .order_by(Announcement.created_at.desc())
    )
    announcements = result.scalars().all()

    return {
        "announcements": [
            {
                "id": a.id,
                "config_key": a.config_key,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "announced_at": str(a.announced_at),
                "effective_from": str(a.effective_from),
            }
            for a in announcements
        ]
    }
