"""C Redemption API schemas: request/response models."""

from pydantic import BaseModel


class RedemptionRequest(BaseModel):
    """Child requests redemption of C balance."""
    amount: str  # Yuan string, e.g. "500.00"
    reason: str = ""


class RedemptionPending(BaseModel):
    """Pending redemption awaiting parent approval."""
    amount: str  # Yuan
    fee: str     # Yuan
    net: str     # Yuan
    c_balance: str  # Yuan
    reason: str
    status: str  # "pending"


class RedemptionApproveRequest(BaseModel):
    """Parent approves or rejects a redemption."""
    amount: str  # Yuan string, must match the pending request
    approved: bool
    reason: str = ""


class RedemptionResult(BaseModel):
    """Result after approval or rejection."""
    status: str  # "approved" or "rejected"
    amount: str  # Yuan
    fee: str | None = None
    net: str | None = None
    c_balance_after: str | None = None
    a_balance_after: str | None = None
    reason: str = ""
