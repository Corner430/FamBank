-- ============================================================
-- FamBank 家庭银行 — 完整数据库 Schema (V2 多租户版本)
-- 所有金额以 BIGINT 存储，单位为"分"
-- 生成日期: 2026-03-01
-- ============================================================


-- ------------------------------------------------------------
-- 1. 用户表
--    phone: 手机号（11位），用于短信验证码登录
--    role/family_id: 加入家庭后才有值
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone       VARCHAR(11)  NOT NULL,
    role        ENUM('parent', 'child') NULL,
    name        VARCHAR(50)  NULL,
    family_id   BIGINT       NULL,
    birth_date  DATE         NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 2. 家庭表（多租户核心）
--    每个家庭独立运行，数据完全隔离
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS family (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    created_by  BIGINT       NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES `user`(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- user.family_id 外键（family 表建完后添加）
ALTER TABLE `user`
    ADD CONSTRAINT fk_user_family FOREIGN KEY (family_id) REFERENCES family(id);


-- ------------------------------------------------------------
-- 3. 邀请码表
--    8位字母数字（排除 O/0/I/1 避免混淆），7天有效期
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invitation (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id   BIGINT       NOT NULL,
    code        VARCHAR(8)   NOT NULL,
    target_role ENUM('parent', 'child') NOT NULL,
    target_name VARCHAR(50)  NOT NULL,
    status      ENUM('pending', 'used', 'revoked', 'expired') NOT NULL DEFAULT 'pending',
    created_by  BIGINT       NOT NULL,
    used_by     BIGINT       NULL,
    expires_at  DATETIME     NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_invitation_code (code),
    INDEX idx_invitation_family_status (family_id, status),
    FOREIGN KEY (family_id)  REFERENCES family(id),
    FOREIGN KEY (created_by) REFERENCES `user`(id),
    FOREIGN KEY (used_by)    REFERENCES `user`(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 4. 短信验证码表
--    60秒冷却、5次尝试上限、15分钟有效期
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sms_code (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone       VARCHAR(11)  NOT NULL,
    code        VARCHAR(6)   NOT NULL,
    expires_at  DATETIME     NOT NULL,
    is_used     BOOLEAN      NOT NULL DEFAULT FALSE,
    attempts    INT          NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sms_code_phone_created (phone, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 5. Refresh Token 表
--    存储 SHA-256 哈希，支持吊销与轮转
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS refresh_token (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  DATETIME     NOT NULL,
    is_revoked  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_refresh_token_hash (token_hash),
    FOREIGN KEY (user_id) REFERENCES `user`(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 6. A/B/C 账户表
--    每个孩子拥有独立的 A（零钱宝）、B（梦想金）、C（牛马金）
--    balance/interest_pool 单位为"分"，CHECK >= 0
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS account (
    id                          BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id                   BIGINT       NOT NULL,
    user_id                     BIGINT       NOT NULL,
    account_type                ENUM('A', 'B', 'C') NOT NULL,
    display_name                VARCHAR(50)  NOT NULL,
    balance                     BIGINT       NOT NULL DEFAULT 0,
    interest_pool               BIGINT       NOT NULL DEFAULT 0,
    is_interest_suspended       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_deposit_suspended        BOOLEAN      NOT NULL DEFAULT FALSE,
    deposit_suspend_until       DATE         NULL,
    last_compliant_purchase_date DATE        NULL,
    created_at                  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_account_user_type (user_id, account_type),
    INDEX idx_account_family (family_id),
    INDEX idx_account_user (user_id),
    CHECK (balance >= 0),
    CHECK (interest_pool >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 7. 月度结算表
--    每个孩子每月最多一次结算，按 (user_id, settlement_date) 唯一
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settlement (
    id                          BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id                   BIGINT       NOT NULL,
    user_id                     BIGINT       NOT NULL,
    settlement_date             DATE         NOT NULL,
    status                      ENUM('completed', 'rolled_back') NOT NULL,
    c_dividend_amount           BIGINT       NOT NULL,
    b_overflow_amount           BIGINT       NOT NULL,
    b_interest_amount           BIGINT       NOT NULL,
    violation_transfer_amount   BIGINT       NOT NULL DEFAULT 0,
    p_active_at_settlement      BIGINT       NOT NULL,
    snapshot_before             JSON         NOT NULL,
    snapshot_after              JSON         NOT NULL,
    created_at                  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_settlement_user_date (user_id, settlement_date),
    INDEX idx_settlement_family (family_id),
    INDEX idx_settlement_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 8. 交易流水表（审计日志，仅追加）
--    Constitution V: 审计可追溯 — 不可 UPDATE/DELETE（由 trigger 保护）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transaction_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id       BIGINT       NOT NULL,
    user_id         BIGINT       NOT NULL,
    `timestamp`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type            VARCHAR(30)  NOT NULL,
    source_account  VARCHAR(20)  NULL,
    target_account  VARCHAR(20)  NULL,
    amount          BIGINT       NOT NULL,
    balance_before  BIGINT       NOT NULL,
    balance_after   BIGINT       NOT NULL,
    charter_clause  VARCHAR(30)  NOT NULL,
    settlement_id   BIGINT       NULL,
    description     VARCHAR(255) NULL,
    INDEX idx_txlog_family (family_id),
    INDEX idx_txlog_user (user_id),
    INDEX idx_txlog_family_ts (family_id, `timestamp` DESC),
    FOREIGN KEY (settlement_id) REFERENCES settlement(id),
    CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 9. 愿望清单 & 物品表
--    锁定期（默认3个月）内不可替换，有效期12个月
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wish_list (
    id                      BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id               BIGINT       NOT NULL,
    user_id                 BIGINT       NOT NULL,
    status                  ENUM('active', 'expired', 'replaced') NOT NULL,
    registered_at           DATE         NOT NULL,
    lock_until              DATE         NOT NULL,
    avg_price               BIGINT       NOT NULL,
    max_price               BIGINT       NOT NULL,
    active_target_item_id   BIGINT       NULL,
    valid_until             DATE         NOT NULL,
    created_at              DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_wishlist_family (family_id),
    INDEX idx_wishlist_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wish_item (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    wish_list_id        BIGINT       NOT NULL,
    name                VARCHAR(100) NOT NULL,
    registered_price    BIGINT       NOT NULL,
    current_price       BIGINT       NOT NULL,
    last_price_update   DATE         NULL,
    verification_url    VARCHAR(500) NULL,
    verification_image  VARCHAR(255) NULL,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wish_list_id) REFERENCES wish_list(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- wish_list.active_target_item_id 外键（wish_item 表建完后添加）
ALTER TABLE wish_list
    ADD CONSTRAINT fk_wish_list_active_target
    FOREIGN KEY (active_target_item_id) REFERENCES wish_item(id);


-- ------------------------------------------------------------
-- 10. 违约记录表
--     penalty_amount = violation_amount × penalty_multiplier（默认2倍）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS violation (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id           BIGINT       NOT NULL,
    user_id             BIGINT       NOT NULL,
    violation_date      DATE         NOT NULL,
    violation_amount    BIGINT       NOT NULL,
    penalty_amount      BIGINT       NOT NULL,
    amount_entered_a    BIGINT       NOT NULL DEFAULT 0,
    is_escalated        BOOLEAN      NOT NULL DEFAULT FALSE,
    description         VARCHAR(255) NOT NULL,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_violation_family (family_id),
    INDEX idx_violation_user (user_id),
    CHECK (violation_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 11. 参数配置表 & 公告表
--     每个家庭独立配置，修改需提前公告（S8: 下月1日生效）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id       BIGINT       NOT NULL,
    `key`           VARCHAR(50)  NOT NULL,
    value           VARCHAR(100) NOT NULL,
    effective_from  DATE         NOT NULL,
    announced_at    DATE         NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_config_family_key (family_id, `key`, effective_from DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS announcement (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id       BIGINT       NOT NULL,
    config_key      VARCHAR(50)  NOT NULL,
    old_value       VARCHAR(100) NOT NULL,
    new_value       VARCHAR(100) NOT NULL,
    announced_at    DATE         NOT NULL,
    effective_from  DATE         NOT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 12. 欠款表
--     A余额不足时产生欠款，下次收入优先偿还
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS debt (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id           BIGINT       NOT NULL,
    user_id             BIGINT       NOT NULL,
    original_amount     BIGINT       NOT NULL,
    remaining_amount    BIGINT       NOT NULL,
    reason              VARCHAR(255) NOT NULL,
    violation_id        BIGINT       NULL,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violation(id),
    CHECK (original_amount > 0),
    CHECK (remaining_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 13. 代管金表
--     C账户溢出资金由家长代管
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escrow (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id   BIGINT       NOT NULL,
    user_id     BIGINT       NOT NULL,
    amount      BIGINT       NOT NULL,
    status      ENUM('pending', 'released') NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at DATETIME     NULL,
    CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 14. C赎回申请表
--     孩子申请 → 家长审批（approve/reject）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS redemption_request (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    family_id       BIGINT       NOT NULL,
    amount          BIGINT       NOT NULL,
    fee             BIGINT       NOT NULL,
    net             BIGINT       NOT NULL,
    reason          VARCHAR(255) NOT NULL DEFAULT '',
    status          ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    requested_by    BIGINT       NOT NULL,
    reviewed_by     BIGINT       NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at     DATETIME     NULL,
    FOREIGN KEY (requested_by) REFERENCES `user`(id),
    FOREIGN KEY (reviewed_by)  REFERENCES `user`(id),
    CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 审计不可变触发器
-- Constitution V: 交易流水仅追加，禁止 UPDATE/DELETE
-- ============================================================

DELIMITER $$

CREATE TRIGGER trg_transaction_log_no_update
BEFORE UPDATE ON transaction_log
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'AUDIT VIOLATION: transaction_log records cannot be updated';
END$$

CREATE TRIGGER trg_transaction_log_no_delete
BEFORE DELETE ON transaction_log
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'AUDIT VIOLATION: transaction_log records cannot be deleted';
END$$

DELIMITER ;
