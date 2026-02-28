# Data Model: FamBank 家庭内部银行核心系统

**Date**: 2026-02-28
**Branch**: `001-fambank-core`
**Storage**: MySQL 8.0 (InnoDB), all monetary values stored as BIGINT cents

## Entities

### User (用户)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 用户唯一标识 |
| role | ENUM('parent','child') | NOT NULL | 角色：parent=甲方, child=乙方 |
| name | VARCHAR(50) | NOT NULL | 显示名称 |
| pin_hash | VARCHAR(255) | NOT NULL | PIN/密码的哈希值 |
| birth_date | DATE | NULL (仅 child 角色必填) | 出生日期（用于18岁锁定计算） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**Uniqueness**: 单家庭场景下 role 唯一（最多1个 parent + 1个 child）。

### Account (账户)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 账户唯一标识 |
| account_type | ENUM('A','B','C') | NOT NULL, UNIQUE | 账户类型 |
| display_name | VARCHAR(50) | NOT NULL | 显示名：零钱宝/梦想金/牛马金 |
| balance | BIGINT | NOT NULL, DEFAULT 0, CHECK(>=0) | 余额（分），A/C的主余额，B的本金池 |
| interest_pool | BIGINT | NOT NULL, DEFAULT 0, CHECK(>=0) | B利息池（分），仅B账户使用，A/C为0 |
| is_interest_suspended | BOOLEAN | NOT NULL, DEFAULT FALSE | B账户是否停息 |
| is_deposit_suspended | BOOLEAN | NOT NULL, DEFAULT FALSE | B账户是否暂停入金 |
| deposit_suspend_until | DATE | NULL | 暂停入金恢复日期 |
| last_compliant_purchase_date | DATE | NULL | 最近合规购买日期（用于12个月停息判断） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**State Transitions (Account B)**:
- 正常 → 停息: 12个月无合规购买（`last_compliant_purchase_date` + 12M < 结算日）
- 停息 → 正常: 完成合规购买或重新备案
- 正常 → 暂停入金: 12个月内第2次违约
- 暂停入金 → 正常: 1个结算周期后自动恢复

### WishList (愿望清单)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 清单唯一标识 |
| status | ENUM('active','expired','replaced') | NOT NULL | 清单状态 |
| registered_at | DATE | NOT NULL | 备案日期 |
| lock_until | DATE | NOT NULL | 锁定到期日（备案日+3个月） |
| avg_price | BIGINT | NOT NULL | 均价（分） |
| max_price | BIGINT | NOT NULL | 最高价（分） |
| active_target_item_id | BIGINT | FK → WishItem.id, NULL | 当前声明的拟购买标的（NULL=默认P_max） |
| valid_until | DATE | NOT NULL | 有效期（备案日+12个月） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**Derived**: `p_active` = 若 `active_target_item_id` 非空则取该标的当前价，否则取 `max_price`。

### WishItem (愿望清单标的)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 标的唯一标识 |
| wish_list_id | BIGINT | FK → WishList.id, NOT NULL | 所属清单 |
| name | VARCHAR(100) | NOT NULL | 标的名称 |
| registered_price | BIGINT | NOT NULL | 备案价（分） |
| current_price | BIGINT | NOT NULL | 当前价（分），默认=备案价 |
| last_price_update | DATE | NULL | 最近价格更新日期 |
| verification_url | VARCHAR(500) | NULL | 可核验链接 |
| verification_image | VARCHAR(255) | NULL | 截图文件路径 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### Transaction (交易记录)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 交易唯一标识 |
| timestamp | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 交易时间 |
| type | VARCHAR(30) | NOT NULL | 操作类型（见下方枚举） |
| source_account | VARCHAR(20) | NULL | 来源账户 |
| target_account | VARCHAR(20) | NULL | 目标账户 |
| amount | BIGINT | NOT NULL, CHECK(>0) | 金额（分） |
| balance_before | BIGINT | NOT NULL | 操作前余额（分） |
| balance_after | BIGINT | NOT NULL | 操作后余额（分） |
| charter_clause | VARCHAR(30) | NOT NULL | 关联章程条款编号（如"第2条"） |
| settlement_id | BIGINT | FK → Settlement.id, NULL | 关联结算记录 |
| description | VARCHAR(255) | NULL | 备注说明 |

**Transaction types (type 枚举)**:
- `income_split_a` / `income_split_b` / `income_split_c`: 入账分流
- `c_dividend`: C派息至A
- `b_overflow`: B溢出至C
- `b_interest`: B计息入利息池
- `a_spend`: A自由消费
- `b_purchase`: B清单购买（扣本金）
- `b_purchase_interest`: B清单购买（扣利息池）
- `violation_penalty`: 违约罚金（B利息池→C）
- `violation_transfer`: 违约等额划转（A→C）
- `c_redemption`: C紧急赎回（C→A净额）
- `c_redemption_fee`: C赎回违约金
- `refund_principal` / `refund_interest`: 退款回B
- `debt_repayment`: 欠款偿还（A→C）
- `escrow_in` / `escrow_out`: 暂存入/出（B暂停入金期间）

**Immutability**: 审计表通过 MySQL trigger 禁止 UPDATE 和 DELETE。

### Settlement (结算记录)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 结算唯一标识 |
| settlement_date | DATE | NOT NULL, UNIQUE | 结算日期（每月唯一） |
| status | ENUM('completed','rolled_back') | NOT NULL | 结算状态 |
| c_dividend_amount | BIGINT | NOT NULL | C派息金额（分） |
| b_overflow_amount | BIGINT | NOT NULL | B溢出金额（分） |
| b_interest_amount | BIGINT | NOT NULL | B利息金额（分） |
| violation_transfer_amount | BIGINT | NOT NULL, DEFAULT 0 | 违约划转金额（分） |
| p_active_at_settlement | BIGINT | NOT NULL | 结算时 P_active（分） |
| snapshot_before | JSON | NOT NULL | 结算前各账户余额快照 |
| snapshot_after | JSON | NOT NULL | 结算后各账户余额快照 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### Violation (违约记录)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 违约唯一标识 |
| violation_date | DATE | NOT NULL | 违约日期 |
| violation_amount | BIGINT | NOT NULL, CHECK(>0) | 违规金额（分） |
| penalty_amount | BIGINT | NOT NULL | 罚金金额（分） = min(B利息池, 2×W) |
| amount_entered_a | BIGINT | NOT NULL, DEFAULT 0 | 已进入A的违约金额（分） |
| is_escalated | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否触发升级条款 |
| description | VARCHAR(255) | NOT NULL | 违约行为描述 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### Config (参数配置)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 配置唯一标识 |
| key | VARCHAR(50) | NOT NULL | 参数名 |
| value | VARCHAR(100) | NOT NULL | 参数值（JSON 编码） |
| effective_from | DATE | NOT NULL | 生效日期 |
| announced_at | DATE | NULL | 公告日期 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**Default config keys**:
- `split_ratio_a`: 15 (百分比整数)
- `split_ratio_b`: 30
- `split_ratio_c`: 55
- `b_tier1_rate`: 200 (月利率万分比，2.0% = 200)
- `b_tier1_limit`: 100000 (分，1000元)
- `b_tier2_rate`: 120 (1.2%)
- `b_tier3_rate`: 30 (0.3%)
- `c_annual_rate`: 500 (年利率万分比，5.0% = 500)
- `penalty_multiplier`: 2
- `redemption_fee_rate`: 10 (百分比，10%)
- `wishlist_lock_months`: 3
- `wishlist_valid_months`: 12
- `b_suspend_months`: 12
- `c_lock_age`: 18

### Announcement (公告)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 公告唯一标识 |
| config_key | VARCHAR(50) | NOT NULL | 变更的参数名 |
| old_value | VARCHAR(100) | NOT NULL | 旧值 |
| new_value | VARCHAR(100) | NOT NULL | 新值 |
| announced_at | DATE | NOT NULL | 公告日期 |
| effective_from | DATE | NOT NULL | 生效日期（下一结算周期后） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### Debt (欠款)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 欠款唯一标识 |
| original_amount | BIGINT | NOT NULL, CHECK(>0) | 原始欠款金额（分） |
| remaining_amount | BIGINT | NOT NULL, CHECK(>=0) | 剩余未还金额（分） |
| reason | VARCHAR(255) | NOT NULL | 产生原因 |
| violation_id | BIGINT | FK → Violation.id, NULL | 关联违约记录 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### Escrow (暂存)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 暂存唯一标识 |
| amount | BIGINT | NOT NULL, CHECK(>0) | 暂存金额（分） |
| status | ENUM('pending','released') | NOT NULL | 状态 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| released_at | DATETIME | NULL | 释放时间 |

## Entity Relationships

```
User (1) ──── (manages) ──── Account (3, fixed: A/B/C)
Account B ──── (constrained by) ──── WishList (0..1 active)
WishList (1) ──── (contains) ──── WishItem (1..N)
Transaction (N) ──── (belongs to) ──── Settlement (0..1)
Violation (1) ──── (triggers) ──── Transaction (1..N)
Violation (1) ──── (may create) ──── Debt (0..1)
Config (N) ──── (announced via) ──── Announcement (0..1)
Account B ──── (may have) ──── Escrow (0..1 pending)
```

## State Machine: Account B

```
                  ┌─────────┐
                  │  Normal │◄──── 合规购买 / 重新备案
                  └────┬────┘
                       │
          12个月无合规购买
                       │
                  ┌────▼────┐
                  │Suspended│  (停息: 不计息, 仍溢出)
                  │(Interest)│
                  └────┬────┘
                       │
              合规购买 / 重新备案
                       │
                  ┌────▼────┐
                  │  Normal │
                  └────┬────┘
                       │
            12月内第2次违约
                       │
                  ┌────▼────┐
                  │Suspended│  (暂停入金+计息, 资金暂存)
                  │(Deposit) │
                  └────┬────┘
                       │
              1个结算周期后
                       │
                  ┌────▼────┐
                  │  Normal │  (暂存资金一次性补入)
                  └─────────┘
```
