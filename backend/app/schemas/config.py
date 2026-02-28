"""Config API schemas: config listing and announcement models."""

from pydantic import BaseModel


class ConfigItem(BaseModel):
    """A single config key-value pair."""
    key: str
    value: str
    effective_from: str


class ConfigListResponse(BaseModel):
    """Response listing all current config values."""
    configs: list[ConfigItem]


class AnnounceRequest(BaseModel):
    """Request to announce a config parameter change."""
    key: str
    new_value: str
    reason: str = ""


class AnnouncementDetail(BaseModel):
    """Details of a created announcement."""
    id: int
    config_key: str
    old_value: str
    new_value: str
    announced_at: str
    effective_from: str
    reason: str = ""
