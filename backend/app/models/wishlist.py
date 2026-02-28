"""WishList and WishItem models."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WishList(Base):
    __tablename__ = "wish_list"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "expired", "replaced"), nullable=False
    )
    registered_at: Mapped[date] = mapped_column(Date, nullable=False)
    lock_until: Mapped[date] = mapped_column(Date, nullable=False)
    avg_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active_target_item_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("wish_item.id"), nullable=True
    )
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class WishItem(Base):
    __tablename__ = "wish_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wish_list_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("wish_list.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    registered_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_price_update: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
