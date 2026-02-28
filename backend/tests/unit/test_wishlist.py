"""Unit tests for wish list calculations.

Tests: avg_price, max_price calculation, P_active switching.
Charter reference: §4.2 (wish list), §4.3 (target)
"""

from datetime import date

import pytest

from app.services.wishlist import calculate_wish_list_stats, get_p_active


class FakeWishList:
    """Minimal stand-in for WishList model in pure unit tests."""

    def __init__(self, max_price: int, active_target_item_id: int | None = None):
        self.max_price = max_price
        self.active_target_item_id = active_target_item_id


class FakeWishItem:
    """Minimal stand-in for WishItem model in pure unit tests."""

    def __init__(self, id: int, current_price: int):
        self.id = id
        self.current_price = current_price


class TestCalculateWishListStats:
    """Test avg_price and max_price calculation from item list."""

    def test_single_item(self):
        """Single item: avg == max == that item's price."""
        items = [{"price": 50000}]  # 500元
        result = calculate_wish_list_stats(items)
        assert result["avg_price"] == 50000
        assert result["max_price"] == 50000

    def test_two_items(self):
        """Two items: avg = (300+500)/2 = 400, max = 500."""
        items = [{"price": 30000}, {"price": 50000}]
        result = calculate_wish_list_stats(items)
        assert result["avg_price"] == 40000
        assert result["max_price"] == 50000

    def test_three_items(self):
        """Three items with varying prices."""
        items = [{"price": 10000}, {"price": 20000}, {"price": 30000}]
        result = calculate_wish_list_stats(items)
        assert result["avg_price"] == 20000
        assert result["max_price"] == 30000

    def test_avg_price_floor_division(self):
        """avg_price uses integer floor division.

        Items: 100, 200, 300 → sum=600, avg=600//3=200 ✓
        Items: 100, 200 → sum=300, avg=300//2=150 ✓
        Items: 100, 100, 200 → sum=400, avg=400//3=133 (floor)
        """
        items = [{"price": 100}, {"price": 100}, {"price": 200}]
        result = calculate_wish_list_stats(items)
        assert result["avg_price"] == 133  # 400 // 3 = 133
        assert result["max_price"] == 200

    def test_all_same_price(self):
        """All items same price: avg == max == that price."""
        items = [{"price": 15000}] * 5
        result = calculate_wish_list_stats(items)
        assert result["avg_price"] == 15000
        assert result["max_price"] == 15000

    def test_empty_items_rejected(self):
        """Empty item list must be rejected."""
        with pytest.raises(ValueError, match="不能为空"):
            calculate_wish_list_stats([])

    def test_large_prices(self):
        """Large prices (high-value items)."""
        items = [{"price": 100000000}, {"price": 200000000}]  # 100万, 200万
        result = calculate_wish_list_stats(items)
        assert result["avg_price"] == 150000000
        assert result["max_price"] == 200000000


class TestGetPActive:
    """Test P_active determination: target item's price or max_price."""

    def test_no_target_returns_max_price(self):
        """No active target → P_active = max_price."""
        wl = FakeWishList(max_price=50000, active_target_item_id=None)
        items = [FakeWishItem(id=1, current_price=30000), FakeWishItem(id=2, current_price=50000)]
        assert get_p_active(wl, items) == 50000

    def test_target_set_returns_target_price(self):
        """Active target set → P_active = target item's current_price."""
        wl = FakeWishList(max_price=50000, active_target_item_id=1)
        items = [FakeWishItem(id=1, current_price=30000), FakeWishItem(id=2, current_price=50000)]
        assert get_p_active(wl, items) == 30000

    def test_target_set_to_max_item(self):
        """Target set to the max-priced item → P_active = max_price."""
        wl = FakeWishList(max_price=50000, active_target_item_id=2)
        items = [FakeWishItem(id=1, current_price=30000), FakeWishItem(id=2, current_price=50000)]
        assert get_p_active(wl, items) == 50000

    def test_target_item_price_updated(self):
        """If target item's price changed, P_active reflects the new price."""
        wl = FakeWishList(max_price=50000, active_target_item_id=1)
        items = [FakeWishItem(id=1, current_price=45000), FakeWishItem(id=2, current_price=50000)]
        assert get_p_active(wl, items) == 45000

    def test_target_missing_from_items_falls_back_to_max(self):
        """If target_item_id references an item not in the list, fallback to max_price."""
        wl = FakeWishList(max_price=50000, active_target_item_id=999)
        items = [FakeWishItem(id=1, current_price=30000), FakeWishItem(id=2, current_price=50000)]
        assert get_p_active(wl, items) == 50000

    def test_single_item_as_target(self):
        """Single item list with that item as target."""
        wl = FakeWishList(max_price=40000, active_target_item_id=1)
        items = [FakeWishItem(id=1, current_price=40000)]
        assert get_p_active(wl, items) == 40000

    def test_p_active_switches_on_clear(self):
        """Simulate clearing target: active_target_item_id = None → reverts to max."""
        wl = FakeWishList(max_price=80000, active_target_item_id=None)
        items = [
            FakeWishItem(id=1, current_price=30000),
            FakeWishItem(id=2, current_price=60000),
            FakeWishItem(id=3, current_price=80000),
        ]
        assert get_p_active(wl, items) == 80000

    def test_p_active_switches_on_declare(self):
        """Simulate declaring target: P_active changes to that item's price."""
        items = [
            FakeWishItem(id=1, current_price=30000),
            FakeWishItem(id=2, current_price=60000),
            FakeWishItem(id=3, current_price=80000),
        ]

        # Before declaring target
        wl_before = FakeWishList(max_price=80000, active_target_item_id=None)
        assert get_p_active(wl_before, items) == 80000

        # After declaring item 1 as target
        wl_after = FakeWishList(max_price=80000, active_target_item_id=1)
        assert get_p_active(wl_after, items) == 30000
