"""Settlement model."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Settlement(Base):
    __tablename__ = "settlement"
    __table_args__ = (
        UniqueConstraint("user_id", "settlement_date", name="uq_settlement_user_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("family.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("completed", "rolled_back"), nullable=False
    )
    c_dividend_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    b_overflow_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    b_interest_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    violation_transfer_amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    p_active_at_settlement: Mapped[int] = mapped_column(BigInteger, nullable=False)
    snapshot_before: Mapped[dict] = mapped_column(JSON, nullable=False)
    snapshot_after: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
