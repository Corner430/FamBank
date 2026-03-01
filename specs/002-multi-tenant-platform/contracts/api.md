# API Contracts: FamBank 多家庭多租户产品化

**Date**: 2026-03-01
**Base URL**: `/api/v1`
**Format**: JSON
**Auth**: Phone + SMS code → JWT (access token 24h + refresh token 30d)
**Baseline**: Extends 001-fambank-core API contracts

## New Endpoints

### Authentication (replaces PIN-based auth)

#### POST /auth/send-code

发送短信验证码到手机号。

**Request**:
```json
{
  "phone": "13800138000"
}
```

**Response 200**:
```json
{
  "message": "验证码已发送",
  "expires_in": 300
}
```

**Response 429**: `{ "error": "请60秒后再试" }`
**Response 429**: `{ "error": "错误次数过多，请15分钟后再试" }`

---

#### POST /auth/verify-code

验证短信码，完成注册或登录。自动识别新用户/已有用户。

**Request**:
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**Response 200** (new user):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "dGVz...",
  "user": {
    "id": 1,
    "phone": "13800138000",
    "family_id": null,
    "role": null,
    "name": null
  },
  "is_new_user": true
}
```

**Response 200** (existing user with family):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "dGVz...",
  "user": {
    "id": 1,
    "phone": "13800138000",
    "family_id": 5,
    "role": "parent",
    "name": "爸爸"
  },
  "is_new_user": false
}
```

**Response 401**: `{ "error": "验证码错误" }`
**Response 401**: `{ "error": "验证码已过期，请重新获取" }`

---

#### POST /auth/refresh

刷新 access token。

**Request**:
```json
{
  "refresh_token": "dGVz..."
}
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "new-dGVz..."
}
```

**Response 401**: `{ "error": "刷新令牌已过期，请重新登录" }`

---

### Family Management (家庭管理)

#### POST /family

创建家庭。需已登录且无家庭。

**Request**:
```json
{
  "name": "张家",
  "creator_name": "爸爸"
}
```

**Note**: `creator_name` 为可选字段，用于设置创建者的家庭内显示名称。未提供时默认为"家长"。

**Response 201**:
```json
{
  "family": {
    "id": 1,
    "name": "张家",
    "created_at": "2026-03-01T10:00:00Z"
  },
  "access_token": "eyJ..."
}
```

**Note**: 返回新 access_token（包含 family_id 和 role=parent）。

**Response 409**: `{ "error": "您已属于一个家庭，不可重复创建" }`
**Response 400**: `{ "error": "家庭名称不能为空" }`

---

#### GET /family

获取当前家庭信息。需已登录且有家庭。

**Response 200**:
```json
{
  "family": {
    "id": 1,
    "name": "张家",
    "created_at": "2026-03-01T10:00:00Z"
  },
  "members": [
    { "id": 1, "name": "爸爸", "role": "parent" },
    { "id": 2, "name": "妈妈", "role": "parent" },
    { "id": 3, "name": "小明", "role": "child" },
    { "id": 4, "name": "小红", "role": "child" }
  ]
}
```

---

#### POST /family/invitations

生成邀请码。需 parent 权限。

**Request**:
```json
{
  "target_role": "child",
  "target_name": "小明"
}
```

**Response 201**:
```json
{
  "invitation": {
    "id": 1,
    "code": "AB3K7M2N",
    "target_role": "child",
    "target_name": "小明",
    "expires_at": "2026-03-08T10:00:00Z"
  }
}
```

---

#### GET /family/invitations

获取邀请码列表。需 parent 权限。

**Response 200**:
```json
{
  "invitations": [
    {
      "id": 1,
      "code": "AB3K7M2N",
      "target_role": "child",
      "target_name": "小明",
      "status": "pending",
      "expires_at": "2026-03-08T10:00:00Z"
    }
  ]
}
```

---

#### DELETE /family/invitations/{id}

撤销邀请码。需 parent 权限。

**Response 200**: `{ "message": "邀请码已撤销" }`
**Response 400**: `{ "error": "邀请码已被使用，无法撤销" }`

---

#### POST /family/join

使用邀请码加入家庭。需已登录且无家庭。

**Request**:
```json
{
  "code": "AB3K7M2N"
}
```

**Response 200**:
```json
{
  "family": {
    "id": 1,
    "name": "张家"
  },
  "role": "child",
  "name": "小明",
  "access_token": "eyJ..."
}
```

**Note**: 返回新 access_token（包含 family_id 和 role）。孩子自动创建 A/B/C 账户。

**Response 400**: `{ "error": "邀请码已过期" }`
**Response 400**: `{ "error": "邀请码已失效" }`
**Response 409**: `{ "error": "您已属于一个家庭" }`

---

### Dashboard (家长聚合视图)

#### GET /family/dashboard

家长查看所有孩子的账户摘要。需 parent 权限。

**Response 200**:
```json
{
  "family_name": "张家",
  "total_assets": "3250.00",
  "children": [
    {
      "user_id": 3,
      "name": "小明",
      "accounts": {
        "A": "100.00",
        "B_principal": "200.00",
        "B_interest_pool": "50.00",
        "C": "300.00"
      },
      "total": "650.00"
    },
    {
      "user_id": 4,
      "name": "小红",
      "accounts": {
        "A": "50.00",
        "B_principal": "150.00",
        "B_interest_pool": "30.00",
        "C": "250.00"
      },
      "total": "480.00"
    }
  ]
}
```

---

## Modified Endpoints (from 001-fambank-core)

### Changes Overview

All existing business endpoints remain at the same paths but with these changes:

1. **Auth**: All endpoints now require JWT Bearer token (instead of PIN-based token). Token carries `user_id`, `family_id`, `role`.
2. **Data filtering**: All queries automatically filter by `family_id` from JWT. No family_id in URL path.
3. **Child context**: Endpoints that operate on a specific child now require `child_id` parameter (for parent operating on a child) or infer from JWT (for child operating on self).

### POST /income — 新增 child_id 参数

家长为指定孩子录入收入。

**Request** (parent):
```json
{
  "child_id": 3,
  "amount": "100.00",
  "description": "压岁钱"
}
```

**Note**: `child_id` required for parent (选择哪个孩子). If family has only one child, still required but could be auto-filled by frontend.

---

### GET /accounts — 新增 child_id 查询参数

**Parent**: `GET /accounts?child_id=3` — 查看指定孩子的账户
**Child**: `GET /accounts` — 自动返回自己的账户（child_id from JWT）

---

### POST /settlement — 按家庭结算

家长触发月度结算，系统对家庭内所有孩子逐个独立执行。

**Response 200**:
```json
{
  "settlement_date": "2026-03-01",
  "results": [
    {
      "child_id": 3,
      "child_name": "小明",
      "settlement_id": 10,
      "status": "completed",
      "steps": { "...same as 001..." }
    },
    {
      "child_id": 4,
      "child_name": "小红",
      "settlement_id": 11,
      "status": "completed",
      "steps": { "...same as 001..." }
    }
  ]
}
```

---

### Other Business Endpoints — child_id Pattern

All other business endpoints follow the same pattern:

| Endpoint | Parent Caller | Child Caller |
|----------|---------------|--------------|
| GET /transactions | `?child_id=3` required | auto-filter by self |
| POST /accounts/a/spend | `child_id` in body | auto-use self |
| POST /accounts/b/purchase | `child_id` in body | auto-use self |
| GET /wishlist | `?child_id=3` required | auto-filter by self |
| POST /wishlist | `child_id` in body | auto-use self |
| POST /violations | `child_id` in body required (parent only) | N/A |
| GET /violations | `?child_id=3` optional | auto-filter by self |
| POST /accounts/c/redemption/request | `child_id` in body | auto-use self |
| GET /config | — (family-level) | — (family-level) |
| POST /config/announce | — (family-level, parent only) | N/A |

---

## Removed Endpoints

| Endpoint | Reason |
|----------|--------|
| POST /auth/login | Replaced by POST /auth/verify-code |
| POST /auth/setup | Replaced by POST /family + invitation flow |
| GET /auth/status | No longer needed (replaced by JWT + family check) |
| PUT /auth/pin | Removed (no PIN) |
| PUT /auth/child-pin | Removed (no PIN) |
