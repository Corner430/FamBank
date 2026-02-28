"""Debt model: family internal debt record."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Debt(Base):
    __tablename__ = "debt"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    original_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    remaining_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    violation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("violation.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
