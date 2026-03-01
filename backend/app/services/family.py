"""Family service: create family, manage invitations, join family.

Handles family creation with auto-config initialization, invitation code
generation, and the join-family flow with automatic account creation for children.
"""

import secrets
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.account import Account
from app.models.family import Family
from app.models.invitation import Invitation
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.config import init_default_config

logger = structlog.get_logger("family")

# Characters for invitation code (exclude confusing: O/0/I/1)
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
INVITATION_EXPIRE_DAYS = 7


async def create_family(
    user_id: int,
    name: str,
    db: AsyncSession,
    creator_name: str | None = None,
) -> dict:
    """Create a new family. The creator becomes parent.

    Returns: {"family": FamilyInfo, "access_token": str}
    Raises ValueError if user already belongs to a family.
    """
    # Check user has no family
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise ValueError("用户不存在")
    if user.family_id is not None:
        raise ValueError("您已属于一个家庭，不可重复创建")

    # Create family
    family = Family(name=name, created_by=user_id)
    db.add(family)
    await db.flush()

    # Update user: set family_id, role, name
    display_name = creator_name.strip() if creator_name else "家长"
    user.family_id = family.id
    user.role = "parent"
    user.name = display_name

    # Initialize default config for this family
    await init_default_config(family.id, db)

    # Generate new access token with updated claims
    access_token = create_access_token(
        user_id=user.id,
        family_id=family.id,
        role="parent",
    )

    await db.commit()
    await db.refresh(family)

    logger.info(
        "family_created",
        family_id=family.id,
        family_name=name,
        creator_id=user_id,
    )

    return {
        "family": {
            "id": family.id,
            "name": family.name,
            "created_at": family.created_at,
        },
        "access_token": access_token,
    }


async def get_family_detail(family_id: int, db: AsyncSession) -> dict:
    """Get family info with member list.

    Returns: {"family": FamilyInfo, "members": [MemberInfo]}
    """
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalars().first()
    if family is None:
        raise ValueError("家庭不存在")

    result = await db.execute(
        select(User).where(User.family_id == family_id).order_by(User.id)
    )
    members = result.scalars().all()

    return {
        "family": {
            "id": family.id,
            "name": family.name,
            "created_at": family.created_at,
        },
        "members": [
            {"id": m.id, "name": m.name, "role": m.role}
            for m in members
        ],
    }


def _generate_code() -> str:
    """Generate a cryptographically secure 8-char alphanumeric invitation code."""
    return "".join(secrets.choice(CODE_CHARS) for _ in range(CODE_LENGTH))


async def create_invitation(
    family_id: int,
    created_by: int,
    target_role: str,
    target_name: str,
    db: AsyncSession,
) -> dict:
    """Create an invitation code for a new family member.

    Returns: {"invitation": InvitationInfo}
    """
    code = _generate_code()
    expires_at = datetime.now(UTC) + timedelta(days=INVITATION_EXPIRE_DAYS)

    invitation = Invitation(
        family_id=family_id,
        code=code,
        target_role=target_role,
        target_name=target_name,
        created_by=created_by,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.commit()

    logger.info(
        "invitation_created",
        family_id=family_id,
        target_role=target_role,
        target_name=target_name,
    )

    return {
        "invitation": {
            "id": invitation.id,
            "code": invitation.code,
            "target_role": invitation.target_role,
            "target_name": invitation.target_name,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
        }
    }


async def list_invitations(family_id: int, db: AsyncSession) -> list[dict]:
    """List all invitations for a family."""
    result = await db.execute(
        select(Invitation)
        .where(Invitation.family_id == family_id)
        .order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()

    return [
        {
            "id": inv.id,
            "code": inv.code,
            "target_role": inv.target_role,
            "target_name": inv.target_name,
            "status": inv.status,
            "expires_at": inv.expires_at,
        }
        for inv in invitations
    ]


async def revoke_invitation(
    invitation_id: int,
    family_id: int,
    db: AsyncSession,
) -> None:
    """Revoke a pending invitation.

    Raises ValueError if invitation is not pending or not found.
    """
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.family_id == family_id,
        )
    )
    invitation = result.scalars().first()

    if invitation is None:
        raise ValueError("邀请码不存在")
    if invitation.status != "pending":
        raise ValueError("邀请码已被使用，无法撤销")

    invitation.status = "revoked"
    await db.commit()

    logger.info("invitation_revoked", invitation_id=invitation_id, family_id=family_id)


async def join_family(user_id: int, code: str, db: AsyncSession) -> dict:
    """Join a family using an invitation code.

    Returns: {"family": FamilyInfo, "role": str, "name": str, "access_token": str}
    Raises ValueError on invalid/expired code or if user already has family.
    """
    # Check user has no family
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise ValueError("用户不存在")
    if user.family_id is not None:
        raise ValueError("您已属于一个家庭")

    # Find invitation
    result = await db.execute(
        select(Invitation).where(
            Invitation.code == code.upper(),
            Invitation.status == "pending",
        )
    )
    invitation = result.scalars().first()

    if invitation is None:
        raise ValueError("邀请码已失效")
    if invitation.expires_at < datetime.now(UTC):
        invitation.status = "expired"
        await db.commit()
        raise ValueError("邀请码已过期")

    # Get family
    result = await db.execute(select(Family).where(Family.id == invitation.family_id))
    family = result.scalars().first()

    # Update user
    user.family_id = invitation.family_id
    user.role = invitation.target_role
    user.name = invitation.target_name

    # Mark invitation as used
    invitation.status = "used"
    invitation.used_by = user_id

    # If child, create A/B/C accounts
    if invitation.target_role == "child":
        display_names = {"A": "零钱宝", "B": "梦想金", "C": "牛马金"}
        for acct_type in ["A", "B", "C"]:
            account = Account(
                family_id=invitation.family_id,
                user_id=user_id,
                account_type=acct_type,
                display_name=display_names[acct_type],
                balance=0,
            )
            db.add(account)

    # Revoke all existing refresh tokens (JWT claims changed)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        )
        .values(is_revoked=True)
    )

    # Generate new access token
    access_token = create_access_token(
        user_id=user.id,
        family_id=family.id,
        role=invitation.target_role,
    )

    await db.commit()
    await db.refresh(family)

    logger.info(
        "user_joined_family",
        user_id=user_id,
        family_id=family.id,
        role=invitation.target_role,
        name=invitation.target_name,
    )

    return {
        "family": {
            "id": family.id,
            "name": family.name,
            "created_at": family.created_at,
        },
        "role": invitation.target_role,
        "name": invitation.target_name,
        "access_token": access_token,
    }
