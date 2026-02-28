"""Auth API endpoints: POST /auth/login, POST /auth/setup."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_token, hash_pin, verify_pin
from app.database import get_db
from app.models.user import User

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
