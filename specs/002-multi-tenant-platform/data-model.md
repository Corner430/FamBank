# Data Model: FamBank 多家庭多租户产品化

**Date**: 2026-03-01
**Branch**: `002-multi-tenant-platform`
**Storage**: MySQL 8.0 (InnoDB), all monetary values stored as BIGINT cents
**Baseline**: Extends 001-fambank-core data model

## New Entities

### Family (家庭)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 家庭唯一标识 |
| name | VARCHAR(100) | NOT NULL | 家庭名称（如"张家"） |
| created_by | BIGINT | FK → user.id, NOT NULL | 创建者用户ID |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### Invitation (邀请码)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 邀请码唯一标识 |
| family_id | BIGINT | FK → family.id, NOT NULL | 所属家庭 |
| code | VARCHAR(8) | NOT NULL, UNIQUE | 8位邀请码（大写字母+数字） |
| target_role | ENUM('parent','child') | NOT NULL | 被邀请人角色 |
| target_name | VARCHAR(50) | NOT NULL | 被邀请人显示名称 |
| status | ENUM('pending','used','revoked','expired') | NOT NULL, DEFAULT 'pending' | 邀请码状态 |
| created_by | BIGINT | FK → user.id, NOT NULL | 创建者（家长） |
| used_by | BIGINT | FK → user.id, NULL | 使用者 |
| expires_at | DATETIME | NOT NULL | 过期时间（创建后7天） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### SmsCode (短信验证码)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 验证码唯一标识 |
| phone | VARCHAR(11) | NOT NULL | 手机号 |
| code | VARCHAR(6) | NOT NULL | 6位验证码 |
| expires_at | DATETIME | NOT NULL | 过期时间（5分钟后） |
| is_used | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否已使用 |
| attempts | INT | NOT NULL, DEFAULT 0 | 验证尝试次数 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**Index**: `(phone, created_at DESC)` — 用于查找最新验证码和频率限制

### RefreshToken (刷新令牌)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | 令牌唯一标识 |
| user_id | BIGINT | FK → user.id, NOT NULL | 所属用户 |
| token_hash | VARCHAR(255) | NOT NULL, UNIQUE | 刷新令牌哈希值 |
| expires_at | DATETIME | NOT NULL | 过期时间（30天后） |
| is_revoked | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否已撤销 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

## Modified Entities (from 001-fambank-core)

### User (用户) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| phone | **ADD** VARCHAR(11), UNIQUE, NOT NULL | 手机号（认证标识） |
| family_id | **ADD** BIGINT, FK → family.id, NULL | 所属家庭（NULL=无家庭） |
| pin_hash | **DROP** | 移除 PIN 码认证 |
| role | **MODIFY** ENUM('parent','child'), NULL | 移除 UNIQUE 约束；无家庭时为 NULL |

**New unique constraint**: `UNIQUE(family_id, name)` — 同一家庭内名称唯一

### Account (账户) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |
| account_type | **MODIFY** 移除 `UNIQUE(account_type)` | 每个孩子各有 A/B/C |

**New unique constraint**: `UNIQUE(user_id, account_type)` — 每个孩子每种类型一个账户

### Config (参数配置) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |

**Modified uniqueness**: 配置查询改为按 `(family_id, key, effective_from)` 确定有效值

### Announcement (公告) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |

### TransactionLog (交易记录) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |

### Settlement (结算记录) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |
| settlement_date | **MODIFY** 移除 `UNIQUE(settlement_date)` | 每个孩子每月独立结算 |

**New unique constraint**: `UNIQUE(user_id, settlement_date)` — 每个孩子每月最多一次结算

### WishList (愿望清单) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |

### Violation (违约记录) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |

### Debt (欠款) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |

### Escrow (暂存) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |
| user_id | **ADD** BIGINT, FK → user.id, NOT NULL | 所属孩子 |

### RedemptionRequest (赎回请求) — 修改

| Field | Change | Description |
|-------|--------|-------------|
| family_id | **ADD** BIGINT, FK → family.id, NOT NULL | 所属家庭 |

`requested_by` 和 `reviewed_by` 已有 user FK，无需额外修改。

## Entity Relationships (updated)

```
Family (1) ──── (has) ──── User (N)
Family (1) ──── (has) ──── Config (N)
Family (1) ──── (has) ──── Announcement (N)
Family (1) ──── (has) ──── Invitation (N)

User[child] (1) ──── (owns) ──── Account (3, A/B/C)
User[child] (1) ──── (has) ──── WishList (0..1 active)
User[child] (1) ──── (has) ──── Settlement (N, per month)
User[child] (1) ──── (has) ──── Violation (N)
User[child] (1) ──── (has) ──── Debt (N)
User[child] (1) ──── (has) ──── Escrow (0..1 pending)
User[child] (1) ──── (has) ──── TransactionLog (N)

User (1) ──── (has) ──── RefreshToken (N)
User (1) ──── (has) ──── SmsCode (N, via phone)

WishList (1) ──── (contains) ──── WishItem (1..N)
Transaction (N) ──── (belongs to) ──── Settlement (0..1)
Violation (1) ──── (may create) ──── Debt (0..1)
```

## Unique Constraints Summary (changed)

| Table | Old Constraint | New Constraint |
|-------|---------------|----------------|
| user | UNIQUE(role) | — (removed) |
| user | — | UNIQUE(phone) |
| user | — | UNIQUE(family_id, name) where family_id IS NOT NULL |
| account | UNIQUE(account_type) | UNIQUE(user_id, account_type) |
| settlement | UNIQUE(settlement_date) | UNIQUE(user_id, settlement_date) |
| config | — | Index on (family_id, key, effective_from) |
| invitation | — | UNIQUE(code) |
| sms_code | — | Index on (phone, created_at DESC) |
| refresh_token | — | UNIQUE(token_hash) |

## Indexes (new)

- `account`: `(family_id)`, `(user_id)`
- `transaction_log`: `(family_id)`, `(user_id)`, `(family_id, timestamp DESC)`
- `settlement`: `(family_id)`, `(user_id)`
- `config`: `(family_id, key, effective_from DESC)`
- `wish_list`: `(family_id)`, `(user_id, status)`
- `violation`: `(family_id)`, `(user_id)`
- `invitation`: `(family_id, status)`
- `sms_code`: `(phone, created_at DESC)`
