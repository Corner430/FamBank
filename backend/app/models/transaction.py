"""Transaction model: audit log entry with all fields from data-model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TransactionLog(Base):
    __tablename__ = "transaction_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("family.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_account: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_account: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_before: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charter_clause: Mapped[str] = mapped_column(String(30), nullable=False)
    settlement_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("settlement.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
