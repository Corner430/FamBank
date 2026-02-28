"""Escrow model: B suspend buffer."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Escrow(Base):
    __tablename__ = "escrow"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(Enum("pending", "released"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
