# FamBank 运维手册

## 1. 部署指南

### 1.1 前端小程序部署

**方式一：微信开发者工具 GUI**

1. 打开**微信开发者工具**，加载 `miniprogram/` 目录
2. 点击工具栏右上角的 **上传** 按钮
3. 填写版本号和备注，提交上传
4. 在**微信公众平台** → 版本管理 → 提交审核 → 发布

**方式二：miniprogram-ci CLI（推荐）**

```bash
miniprogram-ci upload \
  --pp ./miniprogram \
  --pkp ./private.wx93708d49ac4c843c.key \
  --appid wx93708d49ac4c843c \
  --uv "1.0.0" \
  --desc "版本描述" \
  -r 1 --enable-es6 true --enable-es7 true --enable-minify true
```

- 上传密钥文件 `private.*.key` 不得提交到 Git
- 如遇 IP 白名单错误，在「开发设置」中关闭白名单或添加当前 IP

> AppID: `wx93708d49ac4c843c`

### 1.2 云函数部署（微信开发者工具 GUI）

**操作步骤：**

1. 打开微信开发者工具
2. 点击左侧栏 **云开发** 按钮进入控制台
3. 在项目目录树中找到 `cloudfunctions/` 下的目标函数
4. **右键** → **上传并部署：所有文件**

**必须选"所有文件"**，原因：
- 每个云函数的 `package.json` 中通过 `"@fambank/shared": "file:../_shared"` 引用共享模块
- `npm install` 在本地会创建符号链接到 `_shared/` 目录
- "云端安装依赖" 模式在云端执行 `npm install`，但云端无法解析 `file:../_shared` 路径
- "所有文件" 模式会直接上传整个 `node_modules/`（含 `_shared` 的实际文件），确保依赖完整

**部署后注意：**
- CloudBase 会保留热实例约 **30 秒**，期间旧代码仍在服务
- 部署后等待约 30 秒，或用测试请求触发冷启动以验证新代码

### 1.3 _shared 修改后的级联部署

`cloudfunctions/_shared/` 被所有 10 个云函数引用。修改后需要根据改动范围重新部署相关函数：

| 修改的文件 | 需重新部署的函数 |
|-----------|----------------|
| `db.js` | **全部 10 个** |
| `errors.js` | **全部 10 个** |
| `logger.js` | **全部 10 个** |
| `money.js` | accounts, income, settlement, violations, redemption, wishlist, family |
| `auth-helper.js` | 除 config 外的 9 个 |
| `config-loader.js` | income, settlement, violations, redemption, wishlist, config |
| `interest.js` | settlement |
| `overflow.js` | settlement |
| `p-active.js` | settlement |

**级联部署操作：** 逐个右键 → 上传并部署：所有文件。

### 1.4 环境变量配置

每个云函数都需要配置以下环境变量（在 CloudBase 控制台 → 云函数 → 函数配置）：

| 变量名 | 说明 |
|--------|------|
| `MYSQL_ADDRESS` | MySQL 内网地址:port（如 `172.17.0.4:3306`） |
| `MYSQL_USERNAME` | 数据库用户名 |
| `MYSQL_PASSWORD` | 数据库密码（见 CloudBase 控制台，不要写在代码或文档中） |
| `MYSQL_DBNAME` | 数据库名（如 `fambank-prod-5g8v3rta823bda48`） |

### 1.5 VPC 网络配置

云函数需要配置 VPC 才能访问 CloudBase MySQL：

- VPC ID: `vpc-9uv4e7rc`
- 子网 ID: `subnet-4gwwx2xj`

在 CloudBase 控制台 → 云函数 → 函数配置 → 网络配置 中设置。

### 1.6 超时时间配置

- 默认超时 **3 秒**（太短）
- 建议设置为 **20 秒**（在 CloudBase 控制台修改）
- `config.json` 中的超时配置仅作为文档参考，**实际生效的是控制台设置**

特别注意 `settlement` 函数，结算逻辑复杂，务必设为 20s。

---

## 2. 日志查看

### 2.1 CloudBase 控制台查看日志

1. 登录 [CloudBase 控制台](https://console.cloud.tencent.com/tcb)
2. 选择环境 `fambank-prod-5g8v3rta823bda48`
3. 左侧菜单 → **云函数** → 选择函数 → **日志**
4. 可按时间范围筛选，支持关键词搜索

### 2.2 MCP 工具查看日志

如果使用 CloudBase MCP 工具：

```
# 获取函数日志列表
getFunctionLogs(functionName: "income", limit: 20)

# 获取单次调用详细日志
getFunctionLogDetail(functionName: "income", requestId: "abc123...")
```

### 2.3 开发者工具本地调试日志

1. 在微信开发者工具中打开云函数
2. 右键函数 → **本地调试**
3. 构造测试 event，点击执行
4. 控制台查看 `console.log/error/warn` 输出

### 2.4 日志格式说明（JSON 结构化日志）

本项目使用 JSON 结构化日志格式。每条日志是一个 JSON 字符串，包含以下字段：

```json
{
  "timestamp": "2026-03-19T10:30:00.123Z",
  "level": "info|warn|error",
  "func": "income",
  "action": "create",
  "requestId": "abc123def456",
  "message": "描述信息",
  "data": {},
  "error": { "message": "...", "stack": "..." }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | ISO 8601 时间戳 |
| `level` | string | 日志级别：info / warn / error |
| `func` | string | 云函数名称 |
| `action` | string | 当前执行的 action |
| `requestId` | string | CloudBase 请求 ID（可追踪单次调用） |
| `message` | string | 日志消息 |
| `data` | object | 附加数据（可选） |
| `error` | object | 错误信息，含 message 和 stack（仅 error 级别） |

**审计日志** 通过 message 中的 `[AUDIT]` 前缀标记关键金融操作：

```json
{"message": "[AUDIT] income_create", "data": {"childId": 5, "amount": "100.00"}}
```

**日志搜索示例：**
- 搜索所有错误：`"level":"error"`
- 搜索审计日志：`[AUDIT]`
- 搜索特定函数：`"func":"income"`
- 搜索特定请求：`"requestId":"abc123"`

---

## 3. 问题排查

### 3.1 排查流程

```
1. 用户反馈异常
   ↓
2. 确认报错信息（前端显示的 msg 字段）
   ↓
3. 确定函数名和 action
   ↓
4. 去 CloudBase 控制台查看对应函数日志
   ↓
5. 根据日志分类处理：
   ├── 有 JSON 格式错误日志 → 根据 error.message 定位代码问题
   ├── 有 "系统异常" 但无详细错误 → 检查 MySQL 连接
   ├── 无日志输出 → 检查函数是否部署成功、超时配置是否足够
   └── 有 MySQL 错误 → 检查 VPC 配置、环境变量、连接池状态
```

### 3.2 常见错误与解决方案

#### EISDIR: bignumber.js 目录名问题

**现象：** 使用 MCP `updateFunctionCode` 部署时报 `EISDIR: illegal operation on a directory`

**原因：** `bignumber.js` npm 包的目录名以 `.js` 结尾，MCP 工具误将其当作文件处理

**解决：** 不要使用 MCP `updateFunctionCode` 部署。改用微信开发者工具 GUI 部署（右键 → 上传并部署：所有文件）

#### Cannot find module '@fambank/shared'

**现象：** 云函数调用返回 500

**原因：**
1. `node_modules` 被 MCP `updateFunctionCode` 破坏
2. 未正确安装依赖

**解决：**
1. 在本地函数目录执行 `npm install`
2. 确认 `node_modules/@fambank/shared` 存在且指向 `_shared/`
3. 重新使用 GUI 方式部署（上传并部署：所有文件）

#### 401 未授权

**现象：** 返回 `{ code: 401, msg: '未授权' }` 或 `{ code: 401, msg: '用户不存在' }`

**排查：**
1. `OPENID` 为空 → 确认是从小程序端调用（`wx.cloud.callFunction`），不是直接 HTTP 调用
2. 用户不存在 → 检查数据库中 `user` 表是否有该用户的记录

#### 500 系统异常

**现象：** 返回 `{ code: 500, msg: '系统异常' }`

**排查：**
1. 查看函数日志，找到 `"level":"error"` 的 JSON 日志
2. 检查 `error.message` 和 `error.stack`
3. 常见原因：MySQL 连接失败、SQL 语法错误、BigInt 运算异常

#### MySQL LIMIT 参数错误

**现象：** `Incorrect arguments to mysqld_stmt_execute`

**原因：** mysql2 的 prepared statement 不支持 LIMIT/OFFSET 使用 `?` 占位符

**解决：** LIMIT 和 OFFSET 使用 `parseInt()` 转换后直接拼接到 SQL 字符串中

```javascript
const limitVal = parseInt(pageSize);
const offsetVal = (parseInt(page) - 1) * limitVal;
sql += ` LIMIT ${limitVal} OFFSET ${offsetVal}`;
```

#### 连接池耗尽 / ETIMEDOUT

**现象：** 请求超时或报连接错误

**原因：** 连接池 `connectionLimit: 3`，并发请求过多

**排查：**
1. 检查是否有未释放的连接（`conn.release()` 在 `finally` 块中）
2. 检查 VPC 配置是否正确
3. 检查 MySQL 实例是否正常运行

#### 云函数超时

**现象：** 调用无返回或返回超时错误

**排查：**
1. 在 CloudBase 控制台检查函数超时设置（默认 3s 太短）
2. 设置为 20s
3. 特别注意 `settlement` 函数，逻辑复杂耗时较长

#### 部署后旧代码缓存

**现象：** 部署新代码后，函数行为与预期不符

**原因：** CloudBase 热实例会缓存旧代码约 30 秒

**解决：** 等待 30 秒后再测试，或发送测试请求触发冷启动

### 3.3 MCP updateFunctionCode 禁用说明

**严禁使用** `updateFunctionCode` MCP 工具部署云函数，原因：
1. 会破坏 `node_modules/` 中的符号链接和目录结构
2. `bignumber.js` 目录名导致 EISDIR 错误
3. 部署后函数无法正常运行

**唯一可靠的部署方式：** 微信开发者工具 GUI → 右键 → 上传并部署：所有文件

---

## 4. 数据库操作

### 4.1 通过 MCP 查询数据

使用 CloudBase MCP 的 `executeReadOnlySQL` 工具可以安全地查询数据库（只读）：

```
executeReadOnlySQL(sql: "SELECT * FROM user LIMIT 10")
```

### 4.2 常用查询模板

**查用户信息：**
```sql
SELECT id, name, role, family_id, _openid, created_at FROM user WHERE _openid = 'xxx';
```

**查账户余额：**
```sql
SELECT id, user_id, account_type, display_name, balance, interest_pool,
       is_interest_suspended, is_deposit_suspended
FROM account WHERE user_id = 1;
```

**查最近交易：**
```sql
SELECT id, type, source_account, target_account, amount, balance_before,
       balance_after, description, timestamp
FROM transaction_log WHERE user_id = 1
ORDER BY timestamp DESC LIMIT 20;
```

**查结算记录：**
```sql
SELECT id, user_id, settlement_date, c_dividend_amount, b_overflow_amount,
       b_interest_amount, violation_transfer_amount, p_active_at_settlement,
       snapshot_before, snapshot_after
FROM settlement WHERE family_id = 1
ORDER BY settlement_date DESC;
```

**查违规记录：**
```sql
SELECT id, user_id, violation_date, violation_amount, penalty_amount,
       amount_entered_a, is_escalated, description
FROM violation WHERE user_id = 1
ORDER BY violation_date DESC;
```

**查赎回请求：**
```sql
SELECT id, amount, fee, net, reason, status, requested_by, reviewed_by,
       created_at, reviewed_at
FROM redemption_request WHERE family_id = 1
ORDER BY created_at DESC;
```

**查心愿单和物品：**
```sql
SELECT wl.id as list_id, wl.status, wl.registered_at, wl.lock_until,
       wl.valid_until, wl.avg_price, wl.max_price,
       wi.id as item_id, wi.name, wi.registered_price, wi.current_price
FROM wish_list wl
LEFT JOIN wish_item wi ON wl.id = wi.wish_list_id
WHERE wl.user_id = 1
ORDER BY wl.created_at DESC;
```

**查配置项：**
```sql
SELECT * FROM config WHERE family_id = 1;
```

**查公告（待生效配置变更）：**
```sql
SELECT * FROM announcement WHERE family_id = 1 ORDER BY effective_from;
```

**查欠款：**
```sql
SELECT id, user_id, original_amount, remaining_amount, reason, created_at
FROM debt WHERE user_id = 1 AND remaining_amount > 0;
```

**查代管金：**
```sql
SELECT id, user_id, amount, status, released_at, created_at
FROM escrow WHERE user_id = 1 ORDER BY created_at DESC;
```

### 4.3 注意事项

1. **`_openid` 列名**：`user` 表中 openid 列名为 `_openid`（带下划线前缀），这是 CloudBase 惯例
2. **BigInt 类型**：所有金额字段（balance, amount 等）存储为 BIGINT，单位是**分**（cents）。显示时除以 100 转换为元
3. **时区**：MySQL 存储 UTC 时间，`timestamp` 字段为 `DATETIME` 类型，存储的是 UTC 时间
4. **表名关键字**：`user` 是 MySQL 保留字，查询时需要用反引号包裹：`` SELECT * FROM `user` ``

---

## 5. 监控与告警

### 5.1 关键指标监控

建议关注以下指标（可在 CloudBase 控制台查看）：

| 指标 | 关注阈值 | 说明 |
|------|---------|------|
| 函数调用错误率 | > 1% | 可能有代码 bug 或数据库问题 |
| 函数执行时长 | > 10s | 可能连接池耗尽或 SQL 慢查询 |
| 函数调用次数 | 异常波动 | 可能被异常调用 |
| MySQL 连接数 | > 80% | 需要优化连接池或增加配额 |

### 5.2 日志搜索技巧

**搜索所有错误：**
```
"level":"error"
```

**搜索审计日志（关键金融操作）：**
```
[AUDIT]
```

**搜索特定函数的错误：**
```
"func":"settlement","level":"error"
```

**按 requestId 追踪单次请求的完整链路：**
```
"requestId":"具体的请求ID"
```

**搜索特定操作类型的审计：**
```
[AUDIT] income_create
[AUDIT] settlement_execute
[AUDIT] spend_a
```

---

## 附录：云函数清单

| 函数名 | 主要功能 | 关键 action |
|--------|---------|------------|
| `auth` | 登录/用户创建 | login |
| `family` | 家庭管理、邀请 | create, join, detail, createInvitation, dashboard |
| `accounts` | 账户查询、消费、购买 | list, spendA, purchaseB, refundB |
| `income` | 收入分流 | create |
| `transactions` | 交易记录查询 | list |
| `settlement` | 月度结算 | execute, list |
| `violations` | 违约记录 | create, list |
| `redemption` | C赎回申请/审批 | request, approve, listPending |
| `wishlist` | 心愿单管理 | get, create, updatePrice, declareTarget, clearTarget |
| `config` | 配置管理 | list, announce, listAnnouncements |

## 附录：数据库表清单

| 表名 | 说明 |
|------|------|
| `user` | 用户表（家长/孩子） |
| `family` | 家庭表 |
| `invitation` | 邀请码表 |
| `account` | ABC 三个账户 |
| `transaction_log` | 交易流水 |
| `config` | 家庭配置项 |
| `announcement` | 配置变更公告 |
| `settlement` | 结算记录 |
| `violation` | 违约记录 |
| `debt` | 欠款记录 |
| `escrow` | 代管金记录 |
| `redemption_request` | C赎回请求 |
| `wish_list` | 心愿单 |
| `wish_item` | 心愿单物品 |
