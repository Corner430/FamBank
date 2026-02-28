"""Unit tests for violation penalty calculation.

Tests: penalty = min(B_interest_pool, 2 * violation_amount),
       edge cases: pool < 2W, pool = 0.
Charter reference: §7 (违约处理)
"""

from app.services.violation import calculate_penalty


class TestCalculatePenalty:
    """Test penalty calculation: min(B_interest_pool, 2 * violation_amount)."""

    def test_pool_sufficient(self):
        """When pool >= 2*violation, penalty = 2*violation."""
        # Pool=100000 (1000 yuan), violation=20000 (200 yuan)
        # penalty = min(100000, 40000) = 40000
        assert calculate_penalty(100000, 20000) == 40000

    def test_pool_exactly_2x(self):
        """When pool == 2*violation, penalty = pool = 2*violation."""
        assert calculate_penalty(40000, 20000) == 40000

    def test_pool_less_than_2x(self):
        """When pool < 2*violation, penalty = pool (all of it)."""
        # Pool=30000 (300 yuan), violation=20000 (200 yuan)
        # penalty = min(30000, 40000) = 30000
        assert calculate_penalty(30000, 20000) == 30000

    def test_pool_zero(self):
        """When pool = 0, penalty = 0."""
        assert calculate_penalty(0, 20000) == 0

    def test_pool_1_cent(self):
        """When pool = 1 cent, penalty = 1."""
        assert calculate_penalty(1, 20000) == 1

    def test_small_violation(self):
        """Small violation amount with large pool."""
        # Pool=100000, violation=1
        # penalty = min(100000, 2) = 2
        assert calculate_penalty(100000, 1) == 2

    def test_zero_violation(self):
        """Zero violation amount gives zero penalty."""
        assert calculate_penalty(100000, 0) == 0
