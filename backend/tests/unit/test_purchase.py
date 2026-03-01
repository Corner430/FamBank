"""Unit tests for purchase compliance.

Tests: in-list check, 120% substitute limit, balance sufficiency,
deduction order (principal first, then interest pool).
Charter reference: §4.6 (purchase), §6.2 (refund)
"""


from app.services.purchase import calculate_deduction, validate_purchase_compliance


class TestValidatePurchaseCompliance:
    """Test purchase compliance validation (pure function)."""

    def test_valid_purchase_exact_price(self):
        """Purchase at exact item price, sufficient balance."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=50000,
            is_substitute=False,
            b_principal=80000,
            b_interest_pool=10000,
        )
        assert result["ok"] is True
        assert result["error"] is None

    def test_valid_purchase_below_price(self):
        """Purchase below item price (good deal)."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=45000,
            is_substitute=False,
            b_principal=80000,
            b_interest_pool=10000,
        )
        assert result["ok"] is True

    def test_valid_substitute_within_120_percent(self):
        """Substitute purchase within 120% limit."""
        # Item price = 50000, 120% = 60000
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=60000,
            is_substitute=True,
            b_principal=80000,
            b_interest_pool=10000,
        )
        assert result["ok"] is True

    def test_substitute_at_exactly_120_percent(self):
        """Substitute at exactly 120% of item price = allowed."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=60000,  # exactly 120%
            is_substitute=True,
            b_principal=60000,
            b_interest_pool=0,
        )
        assert result["ok"] is True

    def test_substitute_exceeds_120_percent(self):
        """Substitute exceeding 120% of item price = rejected."""
        # Item price = 50000, 120% = 60000, actual = 60001
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=60001,
            is_substitute=True,
            b_principal=100000,
            b_interest_pool=100000,
        )
        assert result["ok"] is False
        assert "120%" in result["error"]

    def test_non_substitute_above_item_price_allowed(self):
        """Non-substitute purchase above item price is allowed (price may have risen)."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=55000,
            is_substitute=False,
            b_principal=80000,
            b_interest_pool=10000,
        )
        assert result["ok"] is True

    def test_insufficient_balance_principal_only(self):
        """Balance insufficient: principal too low, no interest pool."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=50000,
            is_substitute=False,
            b_principal=30000,
            b_interest_pool=0,
        )
        assert result["ok"] is False
        assert "余额不足" in result["error"]

    def test_insufficient_balance_combined(self):
        """Balance insufficient: principal + interest still not enough."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=50000,
            is_substitute=False,
            b_principal=30000,
            b_interest_pool=10000,
        )
        assert result["ok"] is False
        assert "余额不足" in result["error"]

    def test_sufficient_with_interest_pool(self):
        """Principal alone insufficient, but principal + interest is enough."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=50000,
            is_substitute=False,
            b_principal=30000,
            b_interest_pool=20000,
        )
        assert result["ok"] is True

    def test_zero_cost_rejected(self):
        """Zero purchase cost must be rejected."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=0,
            is_substitute=False,
            b_principal=80000,
            b_interest_pool=10000,
        )
        assert result["ok"] is False
        assert "正数" in result["error"]

    def test_negative_cost_rejected(self):
        """Negative purchase cost must be rejected."""
        result = validate_purchase_compliance(
            item_price=50000,
            actual_cost=-100,
            is_substitute=False,
            b_principal=80000,
            b_interest_pool=10000,
        )
        assert result["ok"] is False
        assert "正数" in result["error"]

    def test_substitute_120_percent_rounding(self):
        """120% limit with non-round numbers.

        Item price = 33333 cents.
        120% = 33333 * 120 / 100 = 39999 (integer division).
        Actual = 39999 → allowed.
        """
        result = validate_purchase_compliance(
            item_price=33333,
            actual_cost=39999,
            is_substitute=True,
            b_principal=50000,
            b_interest_pool=0,
        )
        assert result["ok"] is True

    def test_substitute_120_percent_rounding_exceeded(self):
        """120% limit exceeded by 1 cent.

        Item price = 33333, limit = 39999, actual = 40000 → rejected.
        """
        result = validate_purchase_compliance(
            item_price=33333,
            actual_cost=40000,
            is_substitute=True,
            b_principal=50000,
            b_interest_pool=0,
        )
        assert result["ok"] is False


class TestCalculateDeduction:
    """Test deduction order: principal first, then interest pool."""

    def test_fully_from_principal(self):
        """Cost fully covered by principal."""
        result = calculate_deduction(
            actual_cost=30000,
            b_principal=50000,
            b_interest_pool=10000,
        )
        assert result["from_principal"] == 30000
        assert result["from_interest"] == 0

    def test_split_between_principal_and_interest(self):
        """Cost exceeds principal, remainder from interest pool."""
        result = calculate_deduction(
            actual_cost=50000,
            b_principal=30000,
            b_interest_pool=25000,
        )
        assert result["from_principal"] == 30000
        assert result["from_interest"] == 20000

    def test_fully_from_interest(self):
        """Principal is zero, all from interest pool."""
        result = calculate_deduction(
            actual_cost=20000,
            b_principal=0,
            b_interest_pool=30000,
        )
        assert result["from_principal"] == 0
        assert result["from_interest"] == 20000

    def test_exact_principal(self):
        """Cost exactly equals principal."""
        result = calculate_deduction(
            actual_cost=50000,
            b_principal=50000,
            b_interest_pool=10000,
        )
        assert result["from_principal"] == 50000
        assert result["from_interest"] == 0

    def test_exact_total(self):
        """Cost exactly equals principal + interest."""
        result = calculate_deduction(
            actual_cost=70000,
            b_principal=50000,
            b_interest_pool=20000,
        )
        assert result["from_principal"] == 50000
        assert result["from_interest"] == 20000

    def test_zero_cost(self):
        """Zero cost deduction."""
        result = calculate_deduction(
            actual_cost=0,
            b_principal=50000,
            b_interest_pool=10000,
        )
        assert result["from_principal"] == 0
        assert result["from_interest"] == 0

    def test_small_principal_large_cost(self):
        """Small principal, large cost from interest."""
        result = calculate_deduction(
            actual_cost=100000,
            b_principal=1000,
            b_interest_pool=99000,
        )
        assert result["from_principal"] == 1000
        assert result["from_interest"] == 99000

    def test_deduction_sum_equals_cost(self):
        """Sum of deductions must always equal actual_cost (fund conservation)."""
        test_cases = [
            (30000, 50000, 10000),
            (50000, 30000, 25000),
            (20000, 0, 30000),
            (70000, 50000, 20000),
            (1, 1, 0),
            (100000, 0, 100000),
        ]
        for cost, principal, interest in test_cases:
            result = calculate_deduction(cost, principal, interest)
            total_deducted = result["from_principal"] + result["from_interest"]
            assert total_deducted == cost, (
                f"Failed for cost={cost}, principal={principal}, interest={interest}: "
                f"deducted={total_deducted}"
            )
