"""Unit tests for income split calculation.

Tests: 100元, 0.01元 tail-diff, negative input rejection.
Charter reference: §2 (收入入账与自动分流)
"""


import pytest

from app.services.income import calculate_split


class TestIncomeSplit:
    """Test income split with default ratios 15%/30%/55%."""

    def test_split_100_yuan(self):
        """100元 = 10000分 → A=1500, B=3000, C=5500."""
        result = calculate_split(10000, 15, 30, 55)
        assert result == {"A": 1500, "B": 3000, "C": 5500}
        assert sum(result.values()) == 10000

    def test_split_200_yuan(self):
        """200元 = 20000分 → A=3000, B=6000, C=11000."""
        result = calculate_split(20000, 15, 30, 55)
        assert result == {"A": 3000, "B": 6000, "C": 11000}
        assert sum(result.values()) == 20000

    def test_split_1_fen(self):
        """0.01元 = 1分, tail-diff: remainder goes to C (largest ratio).

        A = floor(1 * 15/100) = 0
        B = floor(1 * 30/100) = 0
        C = 1 - 0 - 0 = 1
        """
        result = calculate_split(1, 15, 30, 55)
        assert result == {"A": 0, "B": 0, "C": 1}
        assert sum(result.values()) == 1

    def test_split_3_fen(self):
        """0.03元 = 3分.

        A = floor(3 * 15/100) = 0
        B = floor(3 * 30/100) = 0
        C = 3 - 0 - 0 = 3
        """
        result = calculate_split(3, 15, 30, 55)
        assert result["C"] == 3
        assert sum(result.values()) == 3

    def test_split_7_fen(self):
        """0.07元 = 7分.

        A = floor(7 * 15/100) = 1
        B = floor(7 * 30/100) = 2
        C = 7 - 1 - 2 = 4
        """
        result = calculate_split(7, 15, 30, 55)
        assert result == {"A": 1, "B": 2, "C": 4}
        assert sum(result.values()) == 7

    def test_split_333_fen(self):
        """3.33元 = 333分 — test tail-diff on awkward amount.

        A = floor(333 * 15/100) = floor(49.95) = 49
        B = floor(333 * 30/100) = floor(99.9) = 99
        C = 333 - 49 - 99 = 185
        """
        result = calculate_split(333, 15, 30, 55)
        assert result == {"A": 49, "B": 99, "C": 185}
        assert sum(result.values()) == 333

    def test_split_preserves_total(self):
        """Any amount: sum of splits MUST equal input (fund conservation)."""
        for amount in [1, 2, 3, 10, 99, 100, 999, 10000, 99999, 123456]:
            result = calculate_split(amount, 15, 30, 55)
            assert sum(result.values()) == amount, f"Failed for amount={amount}"

    def test_negative_amount_rejected(self):
        """Negative amounts must be rejected."""
        with pytest.raises(ValueError, match="正数"):
            calculate_split(-100, 15, 30, 55)

    def test_zero_amount_rejected(self):
        """Zero amount must be rejected."""
        with pytest.raises(ValueError, match="正数"):
            calculate_split(0, 15, 30, 55)

    def test_custom_ratios(self):
        """Custom split ratios (20/30/50)."""
        result = calculate_split(10000, 20, 30, 50)
        assert result == {"A": 2000, "B": 3000, "C": 5000}
        assert sum(result.values()) == 10000

    def test_ratios_must_sum_to_100(self):
        """Split ratios must sum to 100."""
        with pytest.raises(ValueError, match="100"):
            calculate_split(10000, 15, 30, 50)
