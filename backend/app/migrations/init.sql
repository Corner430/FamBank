-- FamBank 家庭内部银行 - Database Schema
-- All monetary values stored as BIGINT (cents, 分)

CREATE TABLE IF NOT EXISTS `user` (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role ENUM('parent', 'child') NOT NULL,
    name VARCHAR(50) NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,
    birth_date DATE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS account (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_type ENUM('A', 'B', 'C') NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    balance BIGINT NOT NULL DEFAULT 0,
    interest_pool BIGINT NOT NULL DEFAULT 0,
    is_interest_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    is_deposit_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    deposit_suspend_until DATE NULL,
    last_compliant_purchase_date DATE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_account_type (account_type),
    CHECK (balance >= 0),
    CHECK (interest_pool >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS settlement (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    settlement_date DATE NOT NULL,
    status ENUM('completed', 'rolled_back') NOT NULL,
    c_dividend_amount BIGINT NOT NULL,
    b_overflow_amount BIGINT NOT NULL,
    b_interest_amount BIGINT NOT NULL,
    violation_transfer_amount BIGINT NOT NULL DEFAULT 0,
    p_active_at_settlement BIGINT NOT NULL,
    snapshot_before JSON NOT NULL,
    snapshot_after JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_settlement_date (settlement_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transaction_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type VARCHAR(30) NOT NULL,
    source_account VARCHAR(20) NULL,
    target_account VARCHAR(20) NULL,
    amount BIGINT NOT NULL,
    balance_before BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    charter_clause VARCHAR(30) NOT NULL,
    settlement_id BIGINT NULL,
    description VARCHAR(255) NULL,
    FOREIGN KEY (settlement_id) REFERENCES settlement(id),
    CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wish_list (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    status ENUM('active', 'expired', 'replaced') NOT NULL,
    registered_at DATE NOT NULL,
    lock_until DATE NOT NULL,
    avg_price BIGINT NOT NULL,
    max_price BIGINT NOT NULL,
    active_target_item_id BIGINT NULL,
    valid_until DATE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wish_item (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    wish_list_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    registered_price BIGINT NOT NULL,
    current_price BIGINT NOT NULL,
    last_price_update DATE NULL,
    verification_url VARCHAR(500) NULL,
    verification_image VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wish_list_id) REFERENCES wish_list(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add FK for active_target_item_id after wish_item table exists
ALTER TABLE wish_list
    ADD CONSTRAINT fk_wish_list_active_target
    FOREIGN KEY (active_target_item_id) REFERENCES wish_item(id);

CREATE TABLE IF NOT EXISTS violation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    violation_date DATE NOT NULL,
    violation_amount BIGINT NOT NULL,
    penalty_amount BIGINT NOT NULL,
    amount_entered_a BIGINT NOT NULL DEFAULT 0,
    is_escalated BOOLEAN NOT NULL DEFAULT FALSE,
    description VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (violation_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(50) NOT NULL,
    value VARCHAR(100) NOT NULL,
    effective_from DATE NOT NULL,
    announced_at DATE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS announcement (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(50) NOT NULL,
    old_value VARCHAR(100) NOT NULL,
    new_value VARCHAR(100) NOT NULL,
    announced_at DATE NOT NULL,
    effective_from DATE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS debt (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    original_amount BIGINT NOT NULL,
    remaining_amount BIGINT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    violation_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violation(id),
    CHECK (original_amount > 0),
    CHECK (remaining_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS escrow (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    amount BIGINT NOT NULL,
    status ENUM('pending', 'released') NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at DATETIME NULL,
    CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
