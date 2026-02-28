"""Common Pydantic schemas: Money type (Decimal string <-> integer cents)."""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel


def cents_to_yuan(cents: int) -> str:
    """Convert integer cents to yuan string with 2 decimal places.

    Example: 1234 -> "12.34"
    """
    d = Decimal(cents) / Decimal(100)
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def yuan_to_cents(yuan: str) -> int:
    """Convert yuan string to integer cents.

    Example: "12.34" -> 1234
    Raises ValueError if input has more than 2 decimal places.
    """
    d = Decimal(yuan)
    if d != d.quantize(Decimal("0.01")):
        raise ValueError(f"Amount {yuan} has more than 2 decimal places")
    return int(d * 100)


class MoneyAmount(BaseModel):
    """A monetary amount as a string for JSON transport."""

    amount: str

    def to_cents(self) -> int:
        return yuan_to_cents(self.amount)


class ApiResponse(BaseModel):
    """Base response with optional error."""

    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
