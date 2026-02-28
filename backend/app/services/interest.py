"""Tiered interest calculation service (charter §4.5, §5).

B account: 3-tier monthly interest
C account: 5% annual, monthly dividend to A
"""

from decimal import ROUND_DOWN, Decimal


def calculate_c_dividend(c_balance_cents: int, annual_rate_bps: int) -> int:
    """Calculate C account monthly dividend.

    C_balance × annual_rate / 10000 / 12, floored to cents.

    Args:
        c_balance_cents: C balance in cents
        annual_rate_bps: Annual rate in basis points (万分比), e.g. 500 = 5.0%

    Returns:
        Dividend amount in cents (floored)
    """
    if c_balance_cents <= 0:
        return 0

    balance = Decimal(c_balance_cents)
    rate = Decimal(annual_rate_bps) / Decimal(10000)
    monthly = balance * rate / Decimal(12)
    return int(monthly.to_integral_value(rounding=ROUND_DOWN))


def calculate_b_interest(
    b_principal: int,
    p_active: int,
    tier1_rate: int,
    tier1_limit: int,
    tier2_rate: int,
    tier3_rate: int,
    is_suspended: bool = False,
) -> dict[str, int]:
    """Calculate B account tiered monthly interest.

    Tier1: 0 ~ tier1_limit (default 1000元) at tier1_rate (default 2.0%)
    Tier2: tier1_limit ~ p_active at tier2_rate (default 1.2%)
    Tier3: p_active ~ 1.2×p_active at tier3_rate (default 0.3%)

    All rates are in basis points (万分比): 200 = 2.0%

    Args:
        b_principal: B principal balance in cents
        p_active: Current target price in cents
        tier1_rate: Tier 1 monthly rate in bps
        tier1_limit: Tier 1 upper limit in cents
        tier2_rate: Tier 2 monthly rate in bps
        tier3_rate: Tier 3 monthly rate in bps
        is_suspended: If True, return all zeros

    Returns:
        Dict with tier1, tier2, tier3, total (all in cents)
    """
    if is_suspended or b_principal <= 0:
        return {"tier1": 0, "tier2": 0, "tier3": 0, "total": 0}

    # When no wish list (p_active=0), only Tier1 applies (no Tier2/3 range)
    if p_active <= 0:
        tier1_base = min(b_principal, tier1_limit)
        tier1 = _calc_tier(tier1_base, tier1_rate)
        return {"tier1": tier1, "tier2": 0, "tier3": 0, "total": tier1}

    cap_overflow = int(Decimal(p_active) * Decimal("1.2"))

    # Tier 1: 0 ~ tier1_limit
    tier1_base = min(b_principal, tier1_limit)
    tier1 = _calc_tier(tier1_base, tier1_rate)

    # Tier 2: tier1_limit ~ p_active
    tier2_base = max(0, min(b_principal, p_active) - tier1_limit)
    tier2 = _calc_tier(tier2_base, tier2_rate)

    # Tier 3: p_active ~ cap_overflow
    tier3_base = max(0, min(b_principal, cap_overflow) - p_active)
    tier3 = _calc_tier(tier3_base, tier3_rate)

    total = tier1 + tier2 + tier3

    return {"tier1": tier1, "tier2": tier2, "tier3": tier3, "total": total}


def _calc_tier(base_cents: int, rate_bps: int) -> int:
    """Calculate interest for a single tier: base × rate / 10000, floored."""
    if base_cents <= 0 or rate_bps <= 0:
        return 0
    result = Decimal(base_cents) * Decimal(rate_bps) / Decimal(10000)
    return int(result.to_integral_value(rounding=ROUND_DOWN))
