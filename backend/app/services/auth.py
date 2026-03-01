"""Auth service: SMS code send/verify, token management.

Handles phone+SMS registration/login, code generation, rate limiting,
refresh token creation/rotation, and user find-or-create logic.
"""

import os
import re
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.models.refresh_token import RefreshToken
from app.models.sms_code import SmsCode
from app.models.user import User
from app.services.sms import generate_code, get_dev_code, get_sms_provider

logger = structlog.get_logger("auth_service")

PHONE_REGEX = re.compile(r"^1\d{10}$")
CODE_EXPIRE_MINUTES = 5
RATE_LIMIT_SECONDS = 60
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


async def send_code(phone: str, db: AsyncSession) -> dict:
    """Send a verification code to the given phone number.

    Returns: {"message": "验证码已发送", "expires_in": 300}
    Raises ValueError on validation/rate-limit failures.
    """
    if not PHONE_REGEX.match(phone):
        raise ValueError("手机号格式不正确")

    now = datetime.now(UTC)

    # Check 15-minute lockout: if user has 5+ failed attempts in last 15 minutes
    lockout_cutoff = now - timedelta(minutes=LOCKOUT_MINUTES)
    result = await db.execute(
        select(SmsCode)
        .where(
            SmsCode.phone == phone,
            SmsCode.created_at >= lockout_cutoff,
            SmsCode.attempts >= MAX_ATTEMPTS,
        )
        .order_by(SmsCode.created_at.desc())
        .limit(1)
    )
    locked_code = result.scalars().first()
    if locked_code:
        raise ValueError("错误次数过多，请15分钟后再试")

    # Check 60-second rate limit: if a valid code was sent within the last 60 seconds
    rate_cutoff = now - timedelta(seconds=RATE_LIMIT_SECONDS)
    result = await db.execute(
        select(SmsCode)
        .where(
            SmsCode.phone == phone,
            SmsCode.created_at >= rate_cutoff,
            SmsCode.is_used.is_(False),
        )
        .order_by(SmsCode.created_at.desc())
        .limit(1)
    )
    recent_code = result.scalars().first()
    if recent_code:
        raise ValueError("请60秒后再试")

    # Invalidate any existing unused codes for this phone
    await db.execute(
        update(SmsCode)
        .where(
            SmsCode.phone == phone,
            SmsCode.is_used.is_(False),
        )
        .values(is_used=True)
    )

    # Generate code: dev mode uses fixed code, prod uses random
    sms_mode = os.getenv("SMS_MODE", "dev").lower()
    code = get_dev_code() if sms_mode == "dev" else generate_code()

    # Store the code
    sms_code = SmsCode(
        phone=phone,
        code=code,
        expires_at=now + timedelta(minutes=CODE_EXPIRE_MINUTES),
    )
    db.add(sms_code)
    await db.flush()

    # Send via SMS provider
    provider = get_sms_provider()
    await provider.send_code(phone, code)

    await db.commit()

    logger.info("sms_code_sent", phone=phone)
    return {"message": "验证码已发送", "expires_in": CODE_EXPIRE_MINUTES * 60}


async def verify_code(phone: str, code: str, db: AsyncSession) -> dict:
    """Verify SMS code and return tokens + user info.

    Returns: {"access_token", "refresh_token", "user": UserInfo, "is_new_user": bool}
    Raises ValueError on invalid/expired code.
    """
    now = datetime.now(UTC)

    # Find the latest unexpired, unused code for this phone
    result = await db.execute(
        select(SmsCode)
        .where(
            SmsCode.phone == phone,
            SmsCode.is_used.is_(False),
            SmsCode.expires_at > now,
        )
        .order_by(SmsCode.created_at.desc())
        .limit(1)
    )
    sms_code = result.scalars().first()

    if sms_code is None:
        raise ValueError("验证码已过期，请重新获取")

    # Check attempts
    if sms_code.attempts >= MAX_ATTEMPTS:
        raise ValueError("错误次数过多，请15分钟后再试")

    # Verify code
    if sms_code.code != code:
        sms_code.attempts += 1
        await db.commit()
        raise ValueError("验证码错误")

    # Mark code as used
    sms_code.is_used = True
    await db.flush()

    # Find or create user
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalars().first()
    is_new_user = user is None

    if is_new_user:
        user = User(phone=phone)
        db.add(user)
        await db.flush()

    # Generate tokens
    access_token = create_access_token(
        user_id=user.id,
        family_id=user.family_id,
        role=user.role,
    )
    refresh_token_str = create_refresh_token(user_id=user.id)

    # Store refresh token hash
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(rt)
    await db.commit()

    logger.info(
        "user_authenticated",
        user_id=user.id,
        is_new_user=is_new_user,
        has_family=user.family_id is not None,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "family_id": user.family_id,
            "role": user.role,
            "name": user.name,
        },
        "is_new_user": is_new_user,
    }


async def refresh_token(token: str, db: AsyncSession) -> dict:
    """Validate refresh token and issue new token pair.

    Returns: {"access_token", "refresh_token"}
    Raises ValueError on invalid/expired/revoked token.
    """
    # Decode to get user_id
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise ValueError("刷新令牌已过期，请重新登录")

    user_id = int(payload["sub"])
    token_hash_val = hash_token(token)

    # Find token in DB
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash_val,
            RefreshToken.user_id == user_id,
        )
    )
    rt = result.scalars().first()

    if rt is None or rt.is_revoked or rt.expires_at < datetime.now(UTC):
        raise ValueError("刷新令牌已过期，请重新登录")

    # Revoke old token
    rt.is_revoked = True

    # Get user for current claims
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise ValueError("用户不存在")

    # Issue new pair
    new_access = create_access_token(
        user_id=user.id,
        family_id=user.family_id,
        role=user.role,
    )
    new_refresh = create_refresh_token(user_id=user.id)

    # Store new refresh token
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(new_rt)
    await db.commit()

    logger.info("token_refreshed", user_id=user.id)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
    }
