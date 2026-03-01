"""Auth schemas: PIN change/reset request and response models."""

from pydantic import BaseModel, field_validator


class ChangePinRequest(BaseModel):
    old_pin: str
    new_pin: str

    @field_validator("new_pin")
    @classmethod
    def validate_new_pin(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("新密码至少4位")
        if len(v) > 64:
            raise ValueError("新密码不能超过64位")
        return v


class ResetChildPinRequest(BaseModel):
    parent_pin: str
    new_child_pin: str

    @field_validator("new_child_pin")
    @classmethod
    def validate_new_child_pin(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("新PIN码至少4位")
        if len(v) > 64:
            raise ValueError("新PIN码不能超过64位")
        return v


class PinChangeResponse(BaseModel):
    message: str
