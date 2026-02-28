"""Config and Announcement models."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Config(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    announced_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Announcement(Base):
    __tablename__ = "announcement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str] = mapped_column(String(100), nullable=False)
    new_value: Mapped[str] = mapped_column(String(100), nullable=False)
    announced_at: Mapped[date] = mapped_column(Date, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
