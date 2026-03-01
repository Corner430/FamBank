"""Family schemas: create, join, invitations, dashboard."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class CreateFamilyRequest(BaseModel):
    name: str
    creator_name: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("家庭名称不能为空")
        if len(v) > 100:
            raise ValueError("家庭名称不能超过100个字符")
        return v


class FamilyInfo(BaseModel):
    id: int
    name: str
    created_at: datetime


class FamilyResponse(BaseModel):
    family: FamilyInfo
    access_token: str


class MemberInfo(BaseModel):
    id: int
    name: str | None
    role: str | None


class FamilyDetailResponse(BaseModel):
    family: FamilyInfo
    members: list[MemberInfo]


class CreateInvitationRequest(BaseModel):
    target_role: str
    target_name: str

    @field_validator("target_role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("parent", "child"):
            raise ValueError("角色必须为 parent 或 child")
        return v

    @field_validator("target_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("成员名称不能为空")
        if len(v) > 50:
            raise ValueError("成员名称不能超过50个字符")
        return v


class InvitationInfo(BaseModel):
    id: int
    code: str
    target_role: str
    target_name: str
    status: str
    expires_at: datetime


class InvitationResponse(BaseModel):
    invitation: InvitationInfo


class InvitationListResponse(BaseModel):
    invitations: list[InvitationInfo]


class JoinFamilyRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v or len(v) != 8:
            raise ValueError("邀请码必须为8位")
        return v


class JoinFamilyResponse(BaseModel):
    family: FamilyInfo
    role: str
    name: str
    access_token: str


class ChildAccountSummary(BaseModel):
    A: str
    B_principal: str
    B_interest_pool: str
    C: str


class ChildDashboardItem(BaseModel):
    user_id: int
    name: str | None
    accounts: ChildAccountSummary
    total: str


class DashboardResponse(BaseModel):
    family_name: str
    total_assets: str
    children: list[ChildDashboardItem]
