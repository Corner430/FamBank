"""Auth API endpoints: login, setup, PIN change/reset."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ParentUser
from app.auth import create_token, hash_pin, verify_pin
from app.database import get_db
from app.models.user import User
from app.schemas.auth import ChangePinRequest, PinChangeResponse, ResetChildPinRequest

logger = structlog.get_logger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    pin: str


class SetupRequest(BaseModel):
    parent_name: str
    parent_pin: str
    child_name: str
    child_pin: str
    child_birth_date: str | None = None


class LoginResponse(BaseModel):
    user: dict
    token: str


class SetupResponse(BaseModel):
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with PIN/password. Tries to match against all users."""
    result = await db.execute(select(User))
    users = result.scalars().all()

    for user in users:
        if verify_pin(req.pin, user.pin_hash):
            token = create_token(user.id, user.role)
            logger.info("login_success", user_id=user.id, role=user.role)
            return LoginResponse(
                user={"id": user.id, "role": user.role, "name": user.name},
                token=token,
            )

    logger.warning("login_failed", reason="invalid_pin")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="PIN码错误",
    )


@router.post("/setup", response_model=SetupResponse)
async def setup(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    """First-time setup: create parent and child users."""
    # Check if users already exist
    result = await db.execute(select(User))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="系统已初始化",
        )

    from datetime import date as date_type

    parent = User(
        role="parent",
        name=req.parent_name,
        pin_hash=hash_pin(req.parent_pin),
    )
    child = User(
        role="child",
        name=req.child_name,
        pin_hash=hash_pin(req.child_pin),
        birth_date=(
            date_type.fromisoformat(req.child_birth_date)
            if req.child_birth_date
            else None
        ),
    )

    db.add(parent)
    db.add(child)
    await db.commit()

    logger.info("setup_completed", parent_name=req.parent_name, child_name=req.child_name)
    return SetupResponse(message="初始化成功")


@router.get("/status")
async def auth_status(db: AsyncSession = Depends(get_db)):
    """Check if system has been initialized (users exist)."""
    result = await db.execute(select(User))
    has_users = result.scalars().first() is not None
    return {"initialized": has_users}


@router.put("/pin", response_model=PinChangeResponse)
async def change_pin(
    req: ChangePinRequest,
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Change the parent's own PIN. Requires old PIN verification."""
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    db_user = result.scalars().first()

    if not verify_pin(req.old_pin, db_user.pin_hash):
        logger.warning("change_pin_failed", user_id=user["user_id"], reason="wrong_old_pin")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="原密码错误",
        )

    if req.old_pin == req.new_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与原密码相同",
        )

    db_user.pin_hash = hash_pin(req.new_pin)
    await db.commit()

    logger.info("pin_changed", user_id=user["user_id"])
    return PinChangeResponse(message="密码修改成功")


@router.put("/child-pin", response_model=PinChangeResponse)
async def reset_child_pin(
    req: ResetChildPinRequest,
    user: ParentUser,
    db: AsyncSession = Depends(get_db),
):
    """Reset the child's PIN. Requires parent PIN for secondary auth."""
    # Verify parent PIN (secondary authentication)
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    parent = result.scalars().first()

    if not verify_pin(req.parent_pin, parent.pin_hash):
        logger.warning("reset_child_pin_failed", user_id=user["user_id"], reason="wrong_parent_pin")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理密码错误",
        )

    # Find and update child user
    result = await db.execute(select(User).where(User.role == "child"))
    child = result.scalars().first()
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到乙方用户",
        )

    child.pin_hash = hash_pin(req.new_child_pin)
    await db.commit()

    logger.info("child_pin_reset", parent_id=user["user_id"], child_id=child.id)
    return PinChangeResponse(message="乙方PIN码重置成功")
