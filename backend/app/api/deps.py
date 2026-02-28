"""Auth API dependencies: role-based access control middleware."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.auth import decode_token


async def get_current_user(request: Request) -> dict:
    """Extract and validate the current user from Authorization header."""
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

    return {"user_id": int(payload["sub"]), "role": payload["role"]}


async def require_parent(user: dict = Depends(get_current_user)) -> dict:
    """Require parent role."""
    if user["role"] != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅甲方可执行此操作",
        )
    return user


async def require_any_role(user: dict = Depends(get_current_user)) -> dict:
    """Allow any authenticated user."""
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
ParentUser = Annotated[dict, Depends(require_parent)]
AnyUser = Annotated[dict, Depends(require_any_role)]
