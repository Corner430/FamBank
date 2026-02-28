"""Income API schemas: request and response models."""

from pydantic import BaseModel


class IncomeRequest(BaseModel):
    amount: str  # Yuan string, e.g. "100.00"
    description: str = ""


class IncomeSplitDetail(BaseModel):
    A: str
    B: str
    C: str


class IncomeBalances(BaseModel):
    A: str
    B_principal: str
    B_interest_pool: str
    C: str


class IncomeResponse(BaseModel):
    total: str
    splits: IncomeSplitDetail
    balances: IncomeBalances
    escrow_note: str | None = None
