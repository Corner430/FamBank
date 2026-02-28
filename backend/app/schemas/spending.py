"""Spending Pydantic schemas: request and response models."""

from pydantic import BaseModel


class SpendRequest(BaseModel):
    """Request body for A spending."""

    amount: str  # Yuan string, e.g. "50.00"
    description: str = ""


class SpendResponse(BaseModel):
    """Response for A spending."""

    amount: str  # Yuan string
    balance_before: str  # Yuan string
    balance_after: str  # Yuan string
