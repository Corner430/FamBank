"""Unit tests for interest calculations.

C dividend: C_prin × 5% ÷ 12
B tiered interest: Tier1(0~1000, 2.0%), Tier2(1000~P_active, 1.2%), Tier3(P_active~1.2P, 0.3%)
Charter reference: §4.5, §5
"""

import pytest

from app.services.interest import calculate_b_interest, calculate_c_dividend


class TestCDividend:
    """C账户派息: C_balance × annual_rate / 12."""

    def test_basic_dividend(self):
        """C=120000分(1200元), rate=500(5%), → 1200*5%/12 = 5.00元 = 500分."""
        result = calculate_c_dividend(120000, 500)
        assert result == 500

    def test_zero_balance(self):
        """C=0 → dividend=0."""
        result = calculate_c_dividend(0, 500)
        assert result == 0

    def test_small_balance(self):
        """C=100分(1元), rate=500(5%), → 1*5%/12 = 0.0041... → floor = 0分."""
        result = calculate_c_dividend(100, 500)
        assert result == 0

    def test_large_balance(self):
        """C=10000000分(100000元), → 100000*5%/12 = 416.67元 = 41667分."""
        result = calculate_c_dividend(10000000, 500)
        assert result == 41666  # floor of 416.666...


class TestBInterest:
    """B账户分层利率计息."""

    def test_tier1_only(self):
        """B=80000分(800元), P_active=150000分(1500元).

        Tier1 = 800*2.0% = 16元 = 1600分
        """
        result = calculate_b_interest(
            b_principal=80000,
            p_active=150000,
            tier1_rate=200,
            tier1_limit=100000,
            tier2_rate=120,
            tier3_rate=30,
        )
        assert result["total"] == 1600
        assert result["tier1"] == 1600
        assert result["tier2"] == 0
        assert result["tier3"] == 0

    def test_tier1_and_tier2(self):
        """B=120000分(1200元), P_active=150000分(1500元).

        Tier1 = 1000*2.0% = 20元 = 2000分
        Tier2 = 200*1.2% = 2.4元 = 240分
        Total = 2240分
        """
        result = calculate_b_interest(
            b_principal=120000,
            p_active=150000,
            tier1_rate=200,
            tier1_limit=100000,
            tier2_rate=120,
            tier3_rate=30,
        )
        assert result["tier1"] == 2000
        assert result["tier2"] == 240
        assert result["tier3"] == 0
        assert result["total"] == 2240

    def test_all_three_tiers(self):
        """B=180000分(1800元), P_active=150000分(1500元).

        Cap_overflow = 1.2 × 1500 = 1800 → no overflow
        Tier1 = 1000*2.0% = 20元 = 2000分
        Tier2 = 500*1.2% = 6元 = 600分
        Tier3 = 300*0.3% = 0.9元 = 90分
        Total = 2690分
        """
        result = calculate_b_interest(
            b_principal=180000,
            p_active=150000,
            tier1_rate=200,
            tier1_limit=100000,
            tier2_rate=120,
            tier3_rate=30,
        )
        assert result["tier1"] == 2000
        assert result["tier2"] == 600
        assert result["tier3"] == 90
        assert result["total"] == 2690

    def test_exact_tier1_boundary(self):
        """B=100000分(1000元) = exactly Tier1 limit.

        Tier1 = 1000*2.0% = 2000分
        """
        result = calculate_b_interest(
            b_principal=100000,
            p_active=150000,
            tier1_rate=200,
            tier1_limit=100000,
            tier2_rate=120,
            tier3_rate=30,
        )
        assert result["tier1"] == 2000
        assert result["tier2"] == 0
        assert result["total"] == 2000

    def test_zero_balance(self):
        """B=0 → interest=0."""
        result = calculate_b_interest(
            b_principal=0,
            p_active=150000,
            tier1_rate=200,
            tier1_limit=100000,
            tier2_rate=120,
            tier3_rate=30,
        )
        assert result["total"] == 0

    def test_suspended_returns_zero(self):
        """If suspended=True, all interest = 0."""
        result = calculate_b_interest(
            b_principal=180000,
            p_active=150000,
            tier1_rate=200,
            tier1_limit=100000,
            tier2_rate=120,
            tier3_rate=30,
            is_suspended=True,
        )
        assert result["total"] == 0
        assert result["tier1"] == 0
        assert result["tier2"] == 0
        assert result["tier3"] == 0
