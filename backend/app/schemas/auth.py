"""Auth schemas: phone+SMS code request/response models."""

from pydantic import BaseModel, field_validator


class SendCodeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re

        if not re.match(r"^1\d{10}$", v):
            raise ValueError("手机号格式不正确")
        return v


class SendCodeResponse(BaseModel):
    message: str
    expires_in: int


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re

        if not re.match(r"^1\d{10}$", v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("验证码必须为6位数字")
        return v


class UserInfo(BaseModel):
    id: int
    phone: str
    family_id: int | None = None
    role: str | None = None
    name: str | None = None


class VerifyCodeResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserInfo
    is_new_user: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
