"""Violation Pydantic schemas: request and response models."""

from datetime import date

from pydantic import BaseModel


class ViolationRequest(BaseModel):
    """Request body for recording a violation."""

    violation_amount: str  # Yuan string, e.g. "100.00"
    amount_entered_a: str = "0.00"  # Yuan string
    description: str = ""


class ViolationResponse(BaseModel):
    """Response for violation processing."""

    violation_id: int
    penalty: str  # Yuan string
    is_escalated: bool
    b_interest_pool_before: str  # Yuan string
    b_interest_pool_after: str  # Yuan string
    c_balance_before: str  # Yuan string
    c_balance_after: str  # Yuan string
    deposit_suspend_until: str | None = None


class ViolationItem(BaseModel):
    """Single violation record for list display."""

    id: int
    violation_date: date
    violation_amount: str  # Yuan string
    penalty_amount: str  # Yuan string
    amount_entered_a: str  # Yuan string
    is_escalated: bool
    description: str

    model_config = {"from_attributes": True}


class ViolationListResponse(BaseModel):
    """Violation history list response."""

    items: list[ViolationItem]
    total: int
