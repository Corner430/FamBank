"""Settlement API schemas."""

from pydantic import BaseModel


class SettlementStepDetail(BaseModel):
    amount: str


class SettlementInterestDetail(BaseModel):
    amount: str
    tier1: str
    tier2: str
    tier3: str


class SettlementSteps(BaseModel):
    c_dividend: SettlementStepDetail
    b_overflow: SettlementStepDetail
    b_interest: SettlementInterestDetail
    violation_transfer: SettlementStepDetail


class SettlementBalances(BaseModel):
    A: str
    B_principal: str
    B_interest_pool: str
    C: str


class SettlementResponse(BaseModel):
    settlement_id: int
    date: str
    steps: SettlementSteps
    balances_after: SettlementBalances
