# FamBank - 家庭内部银行

基于「目标储蓄 + 分层利率 + 风控约束」理念的家庭银行微信小程序，帮助孩子培养预算、耐心与契约意识。

## 三账户体系

| 账户 | 名称 | 用途 | 利率 |
|------|------|------|------|
| A | 零钱宝 | 自由消费 | 0% |
| B | 梦想金 | 目标储蓄（愿望清单购物） | 分层月利率 2.0%/1.2%/0.3% |
| C | 牛马金 | 长期锁定（18岁解锁） | 年化 5%，按月派息至 A |

所有收入自动按 15/30/55 比例分配至 A/B/C（比例可配置）。

## 核心流程

- **收入分流**：输入金额 → 自动按比例分配至三个账户
- **A 消费**：自由消费，无需审批
- **B 购物**：只能购买愿望清单中的物品，先扣本金再扣利息池
- **C 赎回**：孩子申请 → 家长审批 → 扣手续费（比例可配置）→ 到账 A
- **月度结算**：C 派息 → B 溢出检查 → B 分层计息 → 违约划转
- **违约惩罚**：B 利息池扣罚 + 下次结算时 A 等额划转至 C

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | 微信小程序原生（WXML/WXSS/JS） |
| 后端 | CloudBase 云函数 × 10（Node.js 16 运行时） |
| 数据库 | CloudBase MySQL，14 张表，金额 BIGINT 分 |
| 认证 | 微信 openid 自动鉴权 |
| 日志 | JSON 结构化日志（createLogger） |

## 快速开始

### 前置要求

- [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
- Node.js 18+（本地开发和 miniprogram-ci 上传用）
- 腾讯云开发 CloudBase 环境（含 MySQL）

### 1. 克隆并导入

```bash
git clone <repo-url> FamBank
```

用微信开发者工具打开 `FamBank/` 目录。

### 2. 安装云函数依赖

```bash
cd cloudfunctions
for func in auth family accounts income transactions settlement violations redemption wishlist config; do
  (cd $func && npm install)
done
```

> `_shared` 模块通过 `"@fambank/shared": "file:../_shared"` 引用，`npm install` 会自动创建符号链接。

### 3. 配置云函数环境变量

在云开发控制台为每个云函数配置以下环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `MYSQL_ADDRESS` | MySQL 地址（host:port） | `172.17.0.4:3306` |
| `MYSQL_USERNAME` | 数据库用户名 | `fambank` |
| `MYSQL_PASSWORD` | 数据库密码 | — |
| `MYSQL_DBNAME` | 数据库名 | `fambank-prod-5g8v3rta823bda48` |

同时需要为每个云函数配置 VPC 网络，使其能访问 MySQL 内网地址。

### 4. 部署云函数

在微信开发者工具中，右键点击每个云函数目录 → 「上传并部署：所有文件」。

> 选择「所有文件」而非「云端安装依赖」，因为 `file:../_shared` 的符号链接在云端无法解析。

也可以使用 `miniprogram-ci` CLI 上传前端代码：

```bash
npm install -g miniprogram-ci
miniprogram-ci upload \
  --pp ./miniprogram \
  --pkp ./private.wx93708d49ac4c843c.key \
  --appid wx93708d49ac4c843c \
  --uv "1.0.0" \
  --desc "版本描述" \
  -r 1 --enable-es6 true --enable-es7 true --enable-minify true
```

> 上传密钥文件需在微信公众平台「开发设置」中生成，`private.*.key` 已在 `.gitignore` 中排除。

### 5. 创建数据库表

通过 CloudBase 控制台执行建表 SQL（14 张表）。

### 6. 设置超时时间

在云开发控制台将每个云函数的超时时间设为 20 秒（默认 3 秒不够用）。

## 使用说明

### 首次使用

1. 打开小程序，微信自动登录
2. 第一个用户创建家庭，成为家长
3. 家长在「设置」页创建邀请码
4. 其他成员输入邀请码加入家庭

### 日常操作

| 操作 | 入口 | 角色 |
|------|------|------|
| 记录收入 | 首页 → 孩子详情 → 记录收入 | 家长 |
| A 消费 / B 购物 | 孩子详情 → 操作按钮 | 家长 |
| C 赎回申请 | 孩子详情 → C赎回 | 孩子/家长 |
| 月度结算 | 设置 → 月度结算 | 家长 |
| 记录违约 | 设置 → 违约记录 | 家长 |
| 管理愿望清单 | 孩子详情 → 愿望清单 | 家长/孩子 |
| 修改参数 | 设置 → 参数配置 | 家长 |

## 项目结构

```
FamBank/
├── miniprogram/              # 小程序前端
│   ├── app.js/json/wxss      # 全局配置
│   ├── pages/                # 11 个页面
│   ├── components/           # 6 个业务组件
│   ├── utils/                # 工具库
│   └── images/               # 图标（TabBar + 小程序头像）
├── cloudfunctions/           # CloudBase 云函数
│   ├── _shared/              # 共享模块（含 logger.js 结构化日志）
│   ├── auth/                 # 登录
│   ├── family/               # 家庭管理
│   ├── accounts/             # 账户操作
│   ├── income/               # 收入分流
│   ├── transactions/         # 交易查询
│   ├── settlement/           # 月度结算
│   ├── violations/           # 违约记录
│   ├── redemption/           # C 赎回
│   ├── wishlist/             # 愿望清单
│   └── config/               # 参数配置
├── docs/                     # 文档（业务章程、运维手册）
├── scripts/                  # 工具脚本
└── project.config.json       # 开发者工具配置
```

## 设计原则

- **金额精度**：数据库和后端使用 BIGINT 分 + BigInt 运算，杜绝浮点误差
- **仅追加审计**：transaction_log 仅 INSERT，不可篡改
- **原子结算**：MySQL advisory lock 防止并发重复结算
- **租户隔离**：所有数据通过 `family_id` 隔离
- **角色控制**：家长/孩子操作权限在云函数层校验
