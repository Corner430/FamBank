"""Unit tests for C redemption fee calculation.

Tests: 10% fee on redemption, insufficient balance, zero amount rejection.
Charter reference: S5 (C-Konto Ruck-Umwandlung / C账户赎回)
"""

import pytest

from app.services.redemption import calculate_redemption_fee


class TestRedemptionFee:
    """Test 10% redemption fee calculation."""

    def test_redeem_500_yuan(self):
        """Redeem 50000 cents (500 yuan) -> fee=5000, net=45000."""
        fee, net = calculate_redemption_fee(50000)
        assert fee == 5000
        assert net == 45000
        assert fee + net == 50000

    def test_redeem_100_yuan(self):
        """Redeem 10000 cents (100 yuan) -> fee=1000, net=9000."""
        fee, net = calculate_redemption_fee(10000)
        assert fee == 1000
        assert net == 9000
        assert fee + net == 10000

    def test_redeem_1_fen(self):
        """Redeem 1 cent -> fee=0 (integer division), net=1."""
        fee, net = calculate_redemption_fee(1)
        assert fee == 0
        assert net == 1
        assert fee + net == 1

    def test_redeem_small_amount(self):
        """Redeem 15 cents -> fee=1, net=14."""
        fee, net = calculate_redemption_fee(15)
        assert fee == 1
        assert net == 14
        assert fee + net == 15

    def test_fee_plus_net_equals_amount(self):
        """For any amount, fee + net must equal the original amount (fund conservation)."""
        for amount in [1, 5, 10, 99, 100, 333, 999, 10000, 50000, 123456]:
            fee, net = calculate_redemption_fee(amount)
            assert fee + net == amount, f"Failed for amount={amount}: fee={fee}, net={net}"

    def test_insufficient_balance_rejected(self):
        """Redeeming more than balance must be rejected."""
        with pytest.raises(ValueError, match="余额不足"):
            calculate_redemption_fee(50000, c_balance=30000)

    def test_exact_balance_allowed(self):
        """Redeeming exactly the balance should be allowed."""
        fee, net = calculate_redemption_fee(50000, c_balance=50000)
        assert fee == 5000
        assert net == 45000

    def test_zero_amount_rejected(self):
        """Zero amount must be rejected."""
        with pytest.raises(ValueError, match="正数"):
            calculate_redemption_fee(0)

    def test_negative_amount_rejected(self):
        """Negative amount must be rejected."""
        with pytest.raises(ValueError, match="正数"):
            calculate_redemption_fee(-100)
