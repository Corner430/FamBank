"""Transaction Pydantic schemas: query params and response models."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class TransactionQuery(BaseModel):
    """Query parameters for transaction list."""

    account: str | None = None
    type: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class TransactionItem(BaseModel):
    """Single transaction record for API response."""

    id: int
    timestamp: datetime
    type: str
    source_account: str | None = None
    target_account: str | None = None
    amount: str  # Yuan string
    balance_before: str  # Yuan string
    balance_after: str  # Yuan string
    charter_clause: str
    description: str | None = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""

    items: list[TransactionItem]
    total: int
    page: int
    per_page: int
    total_pages: int
