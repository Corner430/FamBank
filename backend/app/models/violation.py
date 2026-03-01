"""Violation model."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Violation(Base):
    __tablename__ = "violation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("family.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    violation_date: Mapped[date] = mapped_column(Date, nullable=False)
    violation_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    penalty_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_entered_a: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
