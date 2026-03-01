"""SMS provider abstraction: dev mock + Tencent Cloud SMS."""

import os
import secrets
import string
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger("sms")


class SmsProvider(ABC):
    """Abstract SMS provider interface."""

    @abstractmethod
    async def send_code(self, phone: str, code: str) -> bool:
        """Send verification code to phone. Returns True on success."""
        ...


class DevSmsProvider(SmsProvider):
    """Dev SMS provider: always succeeds, logs code to console."""

    async def send_code(self, phone: str, code: str) -> bool:
        logger.info("dev_sms_sent", phone=phone[-4:], code_length=len(code))
        return True


class TencentSmsProvider(SmsProvider):
    """Tencent Cloud SMS provider."""

    def __init__(self) -> None:
        self.sdk_app_id = os.getenv("TENCENT_SMS_SDK_APP_ID", "")
        self.sign_name = os.getenv("TENCENT_SMS_SIGN_NAME", "")
        self.template_id = os.getenv("TENCENT_SMS_TEMPLATE_ID", "")
        self.secret_id = os.getenv("TENCENT_SECRET_ID", "")
        self.secret_key = os.getenv("TENCENT_SECRET_KEY", "")

    async def send_code(self, phone: str, code: str) -> bool:
        """Send SMS via Tencent Cloud SMS API."""
        # TODO: Implement Tencent Cloud SMS API call when ready for production
        logger.warning(
            "tencent_sms_not_implemented",
            phone=phone,
            msg="Tencent SMS provider not yet implemented, falling back to log",
        )
        return False


def generate_code() -> str:
    """Generate a cryptographically secure 6-digit verification code."""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def get_dev_code() -> str:
    """Return a random code even in dev mode (for security)."""
    return generate_code()


def get_sms_provider() -> SmsProvider:
    """Get SMS provider based on SMS_MODE env var."""
    mode = os.getenv("SMS_MODE", "dev").lower()
    if mode == "tencent":
        return TencentSmsProvider()
    return DevSmsProvider()
