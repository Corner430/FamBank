"""Account model: A/B/C with balance, interest_pool, suspension states."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Account(Base):
    __tablename__ = "account"
    __table_args__ = (
        UniqueConstraint("user_id", "account_type", name="uq_account_user_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("family.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    account_type: Mapped[str] = mapped_column(Enum("A", "B", "C"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    interest_pool: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_interest_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deposit_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deposit_suspend_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_compliant_purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
