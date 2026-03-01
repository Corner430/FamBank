"""User model: phone-based auth, family membership, parent/child roles."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    role: Mapped[str | None] = mapped_column(Enum("parent", "child"), nullable=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    family_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("family.id"), nullable=True
    )
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
