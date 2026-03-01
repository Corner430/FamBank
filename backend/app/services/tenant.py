"""TenantContext: dependency injection for multi-tenant data isolation.

Extracts family_id, user_id, role from JWT claims and provides helper
methods to enforce tenant boundaries at the service layer (Constitution VIII).
"""

from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass
class TenantContext:
    """Holds the current request's tenant information from JWT."""

    user_id: int
    family_id: int | None
    role: str | None

    def get_user_id(self) -> int:
        """Return the authenticated user's ID."""
        return self.user_id

    def get_family_id(self) -> int:
        """Return the user's family_id. Raises 403 if user has no family."""
        if self.family_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请先创建或加入一个家庭",
            )
        return self.family_id

    def get_role(self) -> str:
        """Return the user's role. Raises 403 if user has no role."""
        if self.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请先创建或加入一个家庭",
            )
        return self.role

    def require_parent(self) -> None:
        """Assert that the current user is a parent. Raises 403 otherwise."""
        if self.get_role() != "parent":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅甲方可执行此操作",
            )

    def require_family(self) -> int:
        """Assert user belongs to a family and return family_id."""
        return self.get_family_id()
