"""Invitation model: family join codes."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Invitation(Base):
    __tablename__ = "invitation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("family.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    target_role: Mapped[str] = mapped_column(Enum("parent", "child"), nullable=False)
    target_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "used", "revoked", "expired"),
        nullable=False,
        default="pending",
    )
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    used_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
