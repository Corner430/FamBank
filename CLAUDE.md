# FamBank 开发指南（AI 助手参考）

微信小程序家庭银行，运行在腾讯云 CloudBase 上。

## 环境信息

- CloudBase 环境: `fambank-prod-5g8v3rta823bda48`
- 小程序 AppID: `wx93708d49ac4c843c`
- 数据库: CloudBase MySQL，14 张表
- 云函数运行时: Node.js 16.13（CloudBase 控制台配置）

## 项目结构

```
miniprogram/
  app.js                    # 入口：CloudBase init + 自动登录 + loginReadyCallback 机制
  pages/                    # 11 个页面（每页 js/json/wxml/wxss 四件套）
    index/                  #   首页仪表盘（家长看孩子概览，孩子看自己账户）
    onboarding/             #   引导：创建家庭 / 输入邀请码加入
    child-detail/           #   孩子详情：A消费/B购物/B退款操作
    income/                 #   记录收入（仅家长）
    transactions/           #   交易记录（分页+筛选）
    wishlist/               #   愿望清单管理
    settlement/             #   月度结算（仅家长）
    violation/              #   违约记录（仅家长）
    redemption/             #   C 赎回（孩子申请，家长审批）
    config/                 #   参数配置（仅家长）
    settings/               #   设置页（家庭信息、入口导航）
  components/               # 6 个组件
    account-card/           #   账户卡片展示
    child-selector/         #   孩子选择器（家长视角切换孩子）
    family-member-list/     #   家庭成员列表
    invitation-manager/     #   邀请码创建/撤销
    settlement-report/      #   结算结果展示
    transaction-list/       #   交易列表
  utils/
    cloud.js                #   callCloud(name, action, data) 封装
    auth.js                 #   waitForLogin() / getRole() / getUserId()
    money.js                #   centsToYuan() 前端格式化
    constants.js            #   账户名称、颜色、交易类型标签

cloudfunctions/
  _shared/                  # 共享模块 (@fambank/shared)
    db.js                   #   MySQL 连接池（读 MYSQL_ADDRESS 等环境变量）
    money.js                #   yuanToCents() / centsToYuan() / calculateSplit() — BigInt
    errors.js               #   ok() / badRequest() / serverError() 等响应格式
    auth-helper.js          #   getOrCreateUser / getUserByOpenid / requireParent / resolveChildId
    config-loader.js        #   getConfigValue / getConfigRatios / getAllConfig / DEFAULT_CONFIG
    interest.js             #   calculateCDividend / calculateBInterest
    overflow.js             #   calculateOverflow（B → C 溢出）
    p-active.js             #   getPActive（愿望清单目标价格，排除过期清单）
  auth/                     # login
  family/                   # create / join / detail / dashboard / createInvitation / listInvitations / revokeInvitation
  accounts/                 # list / spendA / purchaseB / refundB
  income/                   # create（仅家长）
  transactions/             # list
  settlement/               # execute / list — 最复杂，使用 advisory lock
  violations/               # create（仅家长）/ list
  redemption/               # request / approve / listPending
  wishlist/                 # get / create / updatePrice / declareTarget / clearTarget
  config/                   # list / announce / listAnnouncements
```

## 关键开发约定

### 金额处理

前端传元字符串（如 `"100.50"`），后端用 `yuanToCents()` 转为 BigInt 分（`10050n`），数据库存 BIGINT。返回前端时用 `centsToYuan()` 转回元字符串。所有运算使用 BigInt，禁止浮点。

### 云函数路由

每个云函数通过 `event.action` 分发：

```javascript
switch (event.action) {
  case 'create': requireParent(user); return await handleCreate(user, event);
  case 'list': return await handleList(user, event);
  default: return badRequest('未知操作');
}
```

### 响应格式

```javascript
// 成功
ok(data)     // → { code: 0, data: ... }
// 失败
badRequest(msg)   // → throws { result: { code: 400, msg } }
serverError()     // → { code: 500, msg: '系统异常，请重试' }
```

### 权限模型

- `requireFamily(user)` — 必须已加入家庭
- `requireParent(user)` — 必须是家长角色
- `resolveChildId(user, event.childId)` — 家长需传 childId，孩子返回自身 id

### 前端调用

```javascript
const { callCloud } = require('../../utils/cloud');
const result = await callCloud('family', 'createInvitation', { targetRole: 'child', targetName: '小明' });
```

### 共享模块引用

各云函数 `package.json` 中：`"@fambank/shared": "file:../_shared"`。本地 `npm install` 会创建符号链接。

**部署注意**：符号链接在云端不可用。必须用「所有文件」模式部署，或在部署前将 `_shared` 实际复制到 `node_modules/@fambank/shared/`。

### MySQL 环境变量

| 变量 | 说明 |
|------|------|
| `MYSQL_ADDRESS` | host:port 格式（如 `172.17.0.4:3306`） |
| `MYSQL_USERNAME` | 数据库用户名 |
| `MYSQL_PASSWORD` | 数据库密码 |
| `MYSQL_DBNAME` | 数据库名 |

`db.js` 从 `MYSQL_ADDRESS` 中 split 出 host 和 port。每个云函数还需配置 VPC 才能连接 MySQL 内网。

### 默认配置（config_override 表为空时生效）

```
split_ratio_a: 15, split_ratio_b: 30, split_ratio_c: 55
b_tier1_rate: 200, b_tier1_limit: 100000 (1000元)
b_tier2_rate: 120, b_tier3_rate: 30
c_annual_rate: 500 (5%), penalty_multiplier: 2
redemption_fee_rate: 10 (10%)
wishlist_lock_months: 3, wishlist_valid_months: 12
b_suspend_months: 12, c_lock_age: 18
```

### 结算并发控制

`settlement` 使用 MySQL advisory lock：`GET_LOCK('fambank_settlement_{childId}', 10)`，每个孩子独立锁，10 秒超时。

### 前端自动化测试（weapp-dev MCP）

通过 `.mcp.json` 配置的 `weapp-dev` MCP 服务器可操作微信开发者工具模拟器，使用前需先启动自动化端口：

```bash
/Applications/wechatwebdevtools.app/Contents/MacOS/cli auto --project /Users/corner/FamBank --auto-port 9420
```

核心工具：`mp_navigate`（导航）、`mp_screenshot`（截图）、`element_tap`（点击）、`element_input`（输入）、`page_getData`（读取页面数据）、`mp_getLogs`（控制台日志）。

### 小程序上传（miniprogram-ci）

使用 `miniprogram-ci` CLI 上传代码到微信后台：

```bash
miniprogram-ci upload \
  --pp ./miniprogram \
  --pkp ./private.wx93708d49ac4c843c.key \
  --appid wx93708d49ac4c843c \
  --uv "1.0.0" \
  --desc "版本描述" \
  -r 1 \
  --enable-es6 true \
  --enable-es7 true \
  --enable-minify true
```

- 上传密钥文件 `private.*.key` 已在 `.gitignore` 中排除，**不要提交到 Git**
- 首次使用需在微信公众平台「开发 → 开发设置 → 小程序代码上传」中生成上传密钥
- 如遇 IP 白名单错误，在「开发设置」中关闭白名单或添加当前 IP
- `-r` 为 robot 编号（1-30），`--uv` 为版本号

### 常见陷阱

- 云函数超时默认 3 秒，需在控制台改为 20 秒
- 部署后热实例可能缓存旧代码约 30 秒
- `auth` 函数在 MCP 端可能显示 `CreateFailed`，通过微信开发者工具部署正常
- `centsToYuan(BigInt)` 返回字符串，`yuanToCents(string)` 返回 BigInt
- `calculateSplit` 余数归入 C 账户
