"""B overflow logic (charter §4.4).

Cap_overflow = 1.2 × P_active
If B_principal strictly > Cap_overflow, excess transfers to C.
"""

from decimal import Decimal


def calculate_overflow(b_principal: int, p_active: int) -> dict[str, int]:
    """Calculate B account overflow.

    Args:
        b_principal: B principal balance in cents
        p_active: Current target price in cents (0 = no wish list, skip overflow)

    Returns:
        Dict with cap_overflow, overflow_amount, b_after (all in cents)
    """
    # No wish list → no overflow constraint
    if p_active <= 0:
        return {
            "cap_overflow": 0,
            "overflow_amount": 0,
            "b_after": b_principal,
        }

    cap_overflow = int(Decimal(p_active) * Decimal("1.2"))

    if b_principal > cap_overflow:
        overflow_amount = b_principal - cap_overflow
        b_after = cap_overflow
    else:
        overflow_amount = 0
        b_after = b_principal

    return {
        "cap_overflow": cap_overflow,
        "overflow_amount": overflow_amount,
        "b_after": b_after,
    }
