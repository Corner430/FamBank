"""WishList API schemas: request and response models."""

from pydantic import BaseModel


class WishItemCreate(BaseModel):
    name: str
    price: str  # Yuan string, e.g. "199.00"
    verification_url: str | None = None


class WishListCreateRequest(BaseModel):
    items: list[WishItemCreate]


class WishItemPriceUpdate(BaseModel):
    price: str  # Yuan string, e.g. "219.00"


class DeclareTargetRequest(BaseModel):
    wish_item_id: int


class WishItemResponse(BaseModel):
    id: int
    name: str
    registered_price: str
    current_price: str
    last_price_update: str | None = None
    verification_url: str | None = None


class WishListResponse(BaseModel):
    id: int
    status: str
    registered_at: str
    lock_until: str
    valid_until: str
    avg_price: str
    max_price: str
    p_active: str
    active_target_item_id: int | None = None
    items: list[WishItemResponse]


class WishListTargetResponse(BaseModel):
    p_active: str
    active_target_item_id: int | None = None
