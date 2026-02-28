"""User model: parent/child roles, PIN hash."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(Enum("parent", "child"), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
