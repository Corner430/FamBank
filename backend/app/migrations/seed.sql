-- Seed default configuration values per charter
-- All rates stored as basis points (万分比) or percentage integers

INSERT IGNORE INTO account (account_type, display_name, balance, interest_pool)
VALUES
    ('A', '零钱宝', 0, 0),
    ('B', '梦想金', 0, 0),
    ('C', '牛马金', 0, 0);

INSERT INTO config (`key`, value, effective_from) VALUES
    ('split_ratio_a', '15', '2026-01-01'),
    ('split_ratio_b', '30', '2026-01-01'),
    ('split_ratio_c', '55', '2026-01-01'),
    ('b_tier1_rate', '200', '2026-01-01'),
    ('b_tier1_limit', '100000', '2026-01-01'),
    ('b_tier2_rate', '120', '2026-01-01'),
    ('b_tier3_rate', '30', '2026-01-01'),
    ('c_annual_rate', '500', '2026-01-01'),
    ('penalty_multiplier', '2', '2026-01-01'),
    ('redemption_fee_rate', '10', '2026-01-01'),
    ('wishlist_lock_months', '3', '2026-01-01'),
    ('wishlist_valid_months', '12', '2026-01-01'),
    ('b_suspend_months', '12', '2026-01-01'),
    ('c_lock_age', '18', '2026-01-01');
