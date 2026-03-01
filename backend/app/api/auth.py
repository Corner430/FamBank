"""Auth API endpoints: send-code, verify-code, refresh (replaces PIN-based auth)."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    RefreshRequest,
    RefreshResponse,
    SendCodeRequest,
    SendCodeResponse,
    UserInfo,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from app.services import auth as auth_service

logger = structlog.get_logger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(req: SendCodeRequest, db: AsyncSession = Depends(get_db)):
    """Send SMS verification code to phone number."""
    try:
        result = await auth_service.send_code(req.phone, db)
        return SendCodeResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(req: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    """Verify SMS code, complete registration or login."""
    try:
        result = await auth_service.verify_code(req.phone, req.code, db)
        return VerifyCodeResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user=UserInfo(**result["user"]),
            is_new_user=result["is_new_user"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    try:
        result = await auth_service.refresh_token(req.refresh_token, db)
        return RefreshResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
