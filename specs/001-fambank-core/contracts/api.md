# API Contracts: FamBank

**Date**: 2026-02-28
**Base URL**: `/api/v1`
**Format**: JSON
**Auth**: PIN-based session token (cookie or header)

## Authentication

### POST /auth/login

Login with PIN/password, returns session.

**Request**:
```json
{
  "pin": "string"
}
```

**Response 200**:
```json
{
  "user": { "id": 1, "role": "parent", "name": "爸爸" },
  "token": "session-token-string"
}
```

**Response 401**: `{ "error": "PIN码错误" }`

---

## Income (入账)

### POST /income

录入收入，自动分流至三账户。需乙方或甲方权限。

**Request**:
```json
{
  "amount": "100.00",
  "description": "压岁钱"
}
```

**Response 200**:
```json
{
  "income_id": 1,
  "total": "100.00",
  "splits": {
    "A": "15.00",
    "B": "30.00",
    "C": "55.00"
  },
  "balances": {
    "A": "15.00",
    "B_principal": "30.00",
    "B_interest_pool": "0.00",
    "C": "55.00"
  },
  "escrow_note": null
}
```

**Response 400**: `{ "error": "收入金额必须为正数" }`

**Note**: 金额以字符串形式传输，避免 JSON 浮点。B暂停入金时，`escrow_note` 返回暂存提示。

---

## Accounts (账户)

### GET /accounts

查询三账户当前余额。

**Response 200**:
```json
{
  "accounts": [
    {
      "type": "A",
      "name": "零钱宝",
      "balance": "45.00"
    },
    {
      "type": "B",
      "name": "梦想金",
      "principal": "90.00",
      "interest_pool": "26.90",
      "is_interest_suspended": false,
      "is_deposit_suspended": false,
      "p_active": "1500.00",
      "cap_overflow": "1800.00"
    },
    {
      "type": "C",
      "name": "牛马金",
      "balance": "165.00"
    }
  ],
  "total_debt": "0.00"
}
```

---

## Spending (消费)

### POST /accounts/a/spend

账户A自由消费。需乙方权限。

**Request**:
```json
{
  "amount": "30.00",
  "description": "买零食"
}
```

**Response 200**:
```json
{
  "transaction_id": 5,
  "amount": "30.00",
  "balance_after": "20.00"
}
```

**Response 400**: `{ "error": "零钱宝余额不足" }`

### POST /accounts/b/purchase

账户B清单购买。需乙方权限，同类替换需甲方确认。

**Request**:
```json
{
  "wish_item_id": 2,
  "actual_cost": "520.00",
  "is_substitute": false,
  "substitute_name": null,
  "description": "购买书包（含运费）"
}
```

**Response 200**:
```json
{
  "transaction_id": 6,
  "cost": "520.00",
  "deducted_from_principal": "520.00",
  "deducted_from_interest": "0.00",
  "principal_after": "480.00",
  "interest_pool_after": "200.00",
  "interest_resumed": false
}
```

**Response 400**: `{ "error": "余额不足（可用 300.00 元，需 480.00 元）" }`
**Response 400**: `{ "error": "替换品价格超出备案价120%上限" }`
**Response 202** (需甲方确认):
```json
{
  "pending_approval_id": 1,
  "message": "同类替换需甲方确认",
  "substitute_name": "双肩包",
  "cost": "580.00",
  "limit": "600.00"
}
```

### POST /accounts/b/purchase/approve

甲方确认同类替换。需甲方权限。

**Request**:
```json
{
  "pending_approval_id": 1,
  "approved": true
}
```

---

## Wish List (愿望清单)

### GET /wishlist

查询当前活跃愿望清单。

**Response 200**:
```json
{
  "wishlist": {
    "id": 1,
    "status": "active",
    "registered_at": "2026-01-15",
    "lock_until": "2026-04-15",
    "valid_until": "2027-01-15",
    "avg_price": "733.33",
    "max_price": "1500.00",
    "p_active": "1500.00",
    "active_target_item": null,
    "items": [
      { "id": 1, "name": "玩具", "registered_price": "200.00", "current_price": "200.00" },
      { "id": 2, "name": "书包", "registered_price": "500.00", "current_price": "500.00" },
      { "id": 3, "name": "游戏机", "registered_price": "1500.00", "current_price": "1500.00" }
    ]
  }
}
```

**Response 200** (无清单): `{ "wishlist": null }`

### POST /wishlist

提交新愿望清单。需乙方权限。

**Request**:
```json
{
  "items": [
    { "name": "玩具", "price": "200.00", "verification_url": "https://..." },
    { "name": "书包", "price": "500.00", "verification_url": "https://..." },
    { "name": "游戏机", "price": "1500.00", "verification_url": "https://..." }
  ]
}
```

**Response 400**: `{ "error": "清单锁定期内不可更换，距解锁还有 30 天" }`

### PATCH /wishlist/items/:id/price

更新标的价格（每月最多1次）。需乙方权限。

**Request**:
```json
{
  "new_price": "520.00"
}
```

**Response 400**: `{ "error": "本月已更新过价格" }`

### POST /wishlist/declare-target

声明拟购买标的（切换 P_active）。需乙方权限。

**Request**:
```json
{
  "wish_item_id": 2
}
```

### DELETE /wishlist/declare-target

撤销声明，P_active 恢复为 P_max。

---

## Settlement (月度结算)

### POST /settlement

触发月度结算。需甲方权限。

**Response 200**:
```json
{
  "settlement_id": 1,
  "date": "2026-02-28",
  "steps": {
    "c_dividend": { "amount": "5.00", "a_balance_after": "50.00" },
    "b_overflow": { "amount": "200.00", "b_principal_after": "1800.00", "c_balance_after": "1365.00" },
    "b_interest": { "amount": "26.90", "tier1": "20.00", "tier2": "6.00", "tier3": "0.90", "b_interest_pool_after": "226.90" },
    "violation_transfer": { "amount": "0.00" }
  },
  "balances_after": {
    "A": "50.00",
    "B_principal": "1800.00",
    "B_interest_pool": "226.90",
    "C": "1365.00"
  }
}
```

**Response 409**: `{ "error": "本月已完成结算" }`

### GET /settlements

查询历史结算记录。

**Query params**: `?page=1&per_page=12`

---

## Violations (违约)

### POST /violations

录入违约记录。需甲方权限。

**Request**:
```json
{
  "violation_amount": "100.00",
  "amount_entered_a": "0.00",
  "description": "套现等价物后变现"
}
```

**Response 200**:
```json
{
  "violation_id": 1,
  "penalty": "200.00",
  "b_interest_pool_after": "300.00",
  "c_balance_after": "1200.00",
  "is_escalated": false,
  "deposit_suspended": false
}
```

---

## Redemption (紧急赎回)

### POST /accounts/c/redemption/request

乙方申请赎回。需乙方权限。

**Request**:
```json
{
  "amount": "500.00",
  "reason": "急需资金"
}
```

**Response 202**:
```json
{
  "pending_redemption_id": 1,
  "amount": "500.00",
  "fee": "50.00",
  "net_to_a": "450.00",
  "message": "等待甲方确认"
}
```

### POST /accounts/c/redemption/approve

甲方确认赎回。需甲方权限。

**Request**:
```json
{
  "pending_redemption_id": 1,
  "approved": true
}
```

---

## Transactions (交易记录)

### GET /transactions

查询交易记录。

**Query params**:
- `account`: A / B / C（筛选账户）
- `type`: 交易类型（筛选类型）
- `from_date` / `to_date`: 时间范围
- `page` / `per_page`: 分页

**Response 200**:
```json
{
  "transactions": [
    {
      "id": 1,
      "timestamp": "2026-02-28T10:30:00Z",
      "type": "income_split_a",
      "source_account": "external",
      "target_account": "A",
      "amount": "15.00",
      "balance_before": "0.00",
      "balance_after": "15.00",
      "charter_clause": "第2条",
      "description": "入账分流：压岁钱"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

---

## Config (参数配置)

### GET /config

查询当前参数配置。

### POST /config/announce

公告参数变更。需甲方权限。

**Request**:
```json
{
  "key": "split_ratio_a",
  "new_value": "20",
  "reason": "调整分流比例"
}
```

**Response 200**:
```json
{
  "announcement_id": 1,
  "key": "split_ratio_a",
  "old_value": "15",
  "new_value": "20",
  "effective_from": "2026-04-01"
}
```
