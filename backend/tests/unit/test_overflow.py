"""Unit tests for B overflow calculation.

Cap_overflow = 1.2 × P_active
If B_principal > Cap_overflow → overflow = B_principal - Cap_overflow → transfer to C
If B_principal == Cap_overflow → no overflow (strict greater than)
Charter reference: §4.4
"""

import pytest

from app.services.overflow import calculate_overflow


class TestBOverflow:

    def test_overflow_occurs(self):
        """B=200000分(2000元), P_active=150000分(1500元).

        Cap = 1.2 × 1500 = 1800元 = 180000分
        Overflow = 2000 - 1800 = 200元 = 20000分
        """
        result = calculate_overflow(200000, 150000)
        assert result["cap_overflow"] == 180000
        assert result["overflow_amount"] == 20000
        assert result["b_after"] == 180000

    def test_no_overflow_below_cap(self):
        """B=100000分(1000元), P_active=150000分(1500元).

        Cap = 180000分, B < Cap → no overflow
        """
        result = calculate_overflow(100000, 150000)
        assert result["overflow_amount"] == 0
        assert result["b_after"] == 100000

    def test_no_overflow_at_cap(self):
        """B exactly equals Cap → NO overflow (strict >)."""
        result = calculate_overflow(180000, 150000)
        assert result["overflow_amount"] == 0
        assert result["b_after"] == 180000

    def test_overflow_with_small_p_active(self):
        """P_active=50000分(500元), B=80000分(800元).

        Cap = 1.2 × 500 = 600元 = 60000分
        Overflow = 800 - 600 = 200元 = 20000分
        """
        result = calculate_overflow(80000, 50000)
        assert result["cap_overflow"] == 60000
        assert result["overflow_amount"] == 20000

    def test_zero_balance(self):
        """B=0 → no overflow."""
        result = calculate_overflow(0, 150000)
        assert result["overflow_amount"] == 0

    def test_zero_p_active(self):
        """P_active=0 (no wish list) → no overflow constraint."""
        result = calculate_overflow(10000, 0)
        assert result["cap_overflow"] == 0
        assert result["overflow_amount"] == 0
        assert result["b_after"] == 10000
