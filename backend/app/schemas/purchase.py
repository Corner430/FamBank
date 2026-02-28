"""Purchase API schemas: request and response models."""

from pydantic import BaseModel


class PurchaseRequest(BaseModel):
    wish_item_id: int
    actual_cost: str  # Yuan string, e.g. "199.00"
    is_substitute: bool = False
    description: str = ""


class PurchaseApproveRequest(BaseModel):
    wish_item_id: int
    actual_cost: str  # Yuan string
    description: str = ""


class RefundRequest(BaseModel):
    purchase_transaction_id: int
    amount: str  # Yuan string


class DeductionDetail(BaseModel):
    from_principal: str
    from_interest: str


class PurchaseResponse(BaseModel):
    item_name: str
    actual_cost: str
    deduction: DeductionDetail
    b_principal_after: str
    b_interest_pool_after: str
    transaction_ids: list[int]
    is_substitute: bool


class RefundResponse(BaseModel):
    refund_amount: str
    refund_to: str
    b_principal_after: str
    b_interest_pool_after: str
    transaction_id: int
