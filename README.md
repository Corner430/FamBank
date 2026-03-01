# FamBank - 家庭内部银行

基于「目标储蓄 + 分层利率 + 风控约束」理念的家庭内部银行系统，帮助孩子培养预算、耐心与契约意识。

## 系统概述

FamBank 实现了一套完整的三账户资产管理体系：

| 账户 | 名称 | 用途 | 利率 |
|------|------|------|------|
| A | 零钱宝 | 自由消费 | 0% |
| B | 梦想金 | 目标储蓄（愿望清单购物） | 分层月利率 2.0%/1.2%/0.3% |
| C | 牛马金 | 长期锁定（18岁解锁） | 年化 5%，按月派息至 A |

**核心流程：**
- 所有收入自动按 15%/30%/55% 分流至 A/B/C
- B 账户关联愿望清单，只能用于购买清单中的物品
- 每月结算：C 派息 → B 溢出检查 → B 计息 → 违约划转
- 违约惩罚：B 利息池 2 倍扣罚 + A 等额划转至 C
- C 赎回：乙方提交申请 → 持久化存库 → 甲方审批 → 扣 10% 手续费到账 A

## 技术栈

**后端：** Python 3.12+ / FastAPI / SQLAlchemy (async) / aiomysql / MySQL 8.0

**前端：** Vue 3 / TypeScript / Vite / Vue Router

## 安全与隐私

项目涉及数据库、部署服务器、CI/CD 流水线，以下是隐私保护措施：

### 敏感信息隔离

| 敏感项 | 保护方式 |
|--------|----------|
| 数据库密码 | 通过 `.env` 文件配置，**已被 `.gitignore` 排除**，不会提交到仓库 |
| JWT 签名密钥 | 通过环境变量 `JWT_SECRET_KEY` 配置，生产环境必须替换默认值 |
| 服务器 SSH 密钥 | 存储在 GitHub Secrets（`SSH_HOST`/`SSH_USER`/`SSH_PRIVATE_KEY`），不在代码中 |
| 用户 PIN 码 | bcrypt 单向哈希存储，数据库中无明文 |

### .gitignore 保护

`.gitignore` 已配置排除以下敏感文件：
- `.env` / `.env.*`（仅保留 `.env.example` 作为模板）
- `.venv/` / `node_modules/`
- `__pycache__/` / `dist/`

### 生产环境部署清单

部署前必须完成：

```bash
# 1. 生成随机 JWT 密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. 在 backend/.env 中配置
JWT_SECRET_KEY=<上面生成的随机字符串>
DB_PASSWORD=<你的强密码>

# 3. 在 GitHub 仓库 Settings → Secrets 中配置
#    SSH_HOST, SSH_USER, SSH_PRIVATE_KEY, SSH_PORT
```

### CI/CD 安全

- CI 中的 MySQL 密码（`fambank`）仅用于 GitHub Actions 临时容器，测试结束即销毁
- 部署通过 SSH 密钥认证（GitHub Secrets），不在代码中暴露任何服务器信息
- CI 配置文件不包含任何真实的生产密码

## 快速部署

### 前置要求

- Python 3.12+
- Node.js 18+（仅构建前端时需要，部署后不需要）
- MySQL 8.0+（本地或云服务器均可）
- [uv](https://github.com/astral-sh/uv) — Python 包管理器

```bash
# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1. 克隆项目

```bash
git clone <repo-url> FamBank && cd FamBank
```

### 2. 准备数据库

**本地 MySQL：**

```bash
mysql -u root -p <<'SQL'
CREATE DATABASE IF NOT EXISTS fambank CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'fambank'@'localhost' IDENTIFIED BY 'fambank';
GRANT ALL PRIVILEGES ON fambank.* TO 'fambank'@'localhost';
FLUSH PRIVILEGES;
SQL
```

**云数据库（腾讯云/阿里云/AWS RDS 等）：**

在云控制台创建 MySQL 8.0 实例，建好 `fambank` 库，拿到主机、端口、用户名、密码即可。

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```bash
# 数据库连接
DB_HOST=localhost
DB_PORT=3306
DB_USER=fambank
DB_PASSWORD=fambank
DB_NAME=fambank

# JWT 签名密钥（生产环境必须修改！）
# 生成方式: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=<你的随机密钥>
```

### 4. 安装后端依赖

```bash
cd backend && uv sync && cd ..
```

### 5. 初始化数据库表和种子数据

```bash
# 本地
mysql -u fambank -pfambank fambank < backend/app/migrations/init.sql
mysql -u fambank -pfambank fambank < backend/app/migrations/triggers.sql
mysql -u fambank -pfambank fambank < backend/app/migrations/seed.sql

# 云数据库
mysql -h <你的主机> -P 3306 -u fambank -p fambank < backend/app/migrations/init.sql
mysql -h <你的主机> -P 3306 -u fambank -p fambank < backend/app/migrations/triggers.sql
mysql -h <你的主机> -P 3306 -u fambank -p fambank < backend/app/migrations/seed.sql
```

### 6. 构建前端

```bash
cd frontend && npm install && npm run build && cd ..
```

构建产物在 `frontend/dist/`，后端会自动托管，无需单独部署前端。

### 7. 启动服务

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 **http://localhost:8000** 即可使用（API + 前端都在这个端口）。

### 8. 初始化系统

首次打开页面会引导创建家长和孩子账号（设置 PIN 码）。

## 使用指南

### 登录

家长和孩子各有自己的 PIN 码。登录后根据角色显示不同的功能菜单。

### 记录收入

进入「收入」页面，输入金额（元），系统自动按 15/30/55 比例分配到三个账户。

```
示例：收入 100 元
  → A 零钱宝：15 元
  → B 梦想金：30 元
  → C 牛马金：55 元
```

### A 零钱宝 - 自由消费

在仪表盘直接消费 A 账户余额，无需审批。

### B 梦想金 - 目标购物

1. **家长创建愿望清单**：添加物品名称和价格
2. **声明目标物品**：孩子可以指定当前最想要的物品
3. **执行购买**：当余额充足时，从 B 扣款（先扣本金，再扣利息池）
4. **替代品购买**：替代品价格不得超过原物品 120%，需家长审批

### C 牛马金 - 长期储蓄与赎回

- 每月结算时自动计息（年化 5%，按月派息至 A）
- 18 岁前锁定，提前赎回需扣 10% 手续费（家长审批）
- **赎回流程**：乙方提交申请 → 请求持久化存库 → 甲方在总览页审批 → 批准后扣费到账 A
- 刷新页面或切换登录，待审批记录不会丢失

### 月度结算（家长操作）

进入「结算」页面点击执行，系统依次完成：

1. **C 派息 → A**：按年化 5% 计算月度利息
2. **B 溢出检查**：若 B 本金 > 1.2 × 目标物品价格，溢出部分转入 C
3. **B 分层计息**：
   - 第一层（≤P_active）：月利率 2.0%
   - 第二层（P_active ~ 1000 元）：月利率 1.2%
   - 第三层（> 1000 元）：月利率 0.3%
4. **违约划转**：A 中的违约等额金额转入 C

### 违约处理（家长操作）

记录违约事件，系统自动：
- 从 B 利息池扣除 min(利息池, 2 × 违约金额)
- 记录 A 账户的等额划转（在下次结算时执行）

### 参数调整（家长操作）

家长可以公告调整系统参数（如利率、分流比例），公告生效日期为下月 1 日。

## API 接口概览

所有接口前缀 `/api/v1`，需在请求头中携带 `Authorization: Bearer <token>`。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /auth/setup | 首次初始化 | 公开 |
| POST | /auth/login | 登录获取 token | 公开 |
| GET | /auth/status | 检查是否已初始化 | 公开 |
| GET | /accounts | 查看三账户余额 | 任意 |
| POST | /income | 记录收入 | 任意 |
| POST | /accounts/a/spend | A 消费 | 任意 |
| POST | /accounts/b/purchase | B 购买 | 任意 |
| POST | /accounts/b/purchase/approve | 审批替代品购买 | 家长 |
| POST | /accounts/b/refund | B 退款 | 家长 |
| POST | /settlement | 执行月度结算 | 家长 |
| GET | /settlements | 结算历史 | 家长 |
| POST | /accounts/c/redemption/request | C 赎回申请 | 任意 |
| POST | /accounts/c/redemption/approve | 审批 C 赎回 | 家长 |
| GET | /accounts/c/redemption/pending | 查看待审批赎回 | 任意 |
| GET | /wishlist | 查看愿望清单 | 任意 |
| POST | /wishlist | 创建愿望清单 | 家长 |
| PATCH | /wishlist/items/{id}/price | 更新物品价格 | 任意 |
| POST | /wishlist/declare-target | 声明目标物品 | 任意 |
| DELETE | /wishlist/declare-target | 清除目标 | 任意 |
| GET | /transactions | 交易记录查询 | 任意 |
| POST | /violations | 记录违约 | 家长 |
| GET | /violations | 违约历史 | 任意 |
| GET | /config | 查看配置参数 | 家长 |
| POST | /config/announce | 公告参数调整 | 家长 |
| GET | /config/announcements | 公告列表 | 家长 |

详细接口文档请访问 Swagger UI：http://localhost:8000/docs

## 项目结构

```
FamBank/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 路由（9 个模块）
│   │   ├── models/        # SQLAlchemy ORM 模型
│   │   ├── schemas/       # Pydantic 请求/响应模型
│   │   ├── services/      # 业务逻辑层
│   │   ├── migrations/    # SQL 建表、触发器、种子数据
│   │   ├── middleware/    # 请求日志中间件
│   │   ├── auth.py        # JWT + bcrypt 认证
│   │   ├── database.py    # 异步数据库连接
│   │   ├── logging_config.py # structlog 结构化日志配置
│   │   └── main.py        # FastAPI 入口
│   ├── tests/
│   │   ├── unit/          # 纯函数单元测试（无 DB）
│   │   └── integration/   # 数据库集成测试
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/         # 8 个 Vue 页面
│   │   ├── components/    # 可复用组件
│   │   ├── services/      # API 调用层
│   │   └── router/        # Vue Router 配置
│   └── package.json
├── deploy/
│   ├── fambank.service    # systemd 服务单元
│   └── setup.sh           # 一键部署脚本
├── .github/workflows/
│   └── ci-deploy.yml      # CI/CD 流水线
└── doc/
    └── 家庭内部银行-分层资产管理章程.md  # 章程原文
```

## 运行测试

```bash
# 创建测试数据库（首次）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fambank_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL ON fambank_test.* TO 'fambank'@'localhost';"

# 运行全部测试（124 个）
cd backend && uv run pytest tests/ -v
```

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，按需修改：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_HOST` | MySQL 主机地址 | `localhost` |
| `DB_PORT` | MySQL 端口 | `3306` |
| `DB_USER` | MySQL 用户名 | `fambank` |
| `DB_PASSWORD` | MySQL 密码 | `fambank` |
| `DB_NAME` | 数据库名 | `fambank` |
| `DATABASE_URL` | 完整连接串（设置后覆盖上面的拆分字段） | - |
| `JWT_SECRET_KEY` | JWT 签名密钥（**生产环境必须修改**） | `fambank-dev-only-...` |
| `TEST_DATABASE_URL` | 测试库连接串（仅开发时需要） | - |
| `LOG_LEVEL` | 日志级别（DEBUG/INFO/WARNING/ERROR） | `INFO` |

## 日志

系统使用 structlog 输出结构化 JSON 日志（每行一条 JSON），适配 journald 和日志采集平台。

```json
{"event":"request_finished","level":"info","logger":"http","timestamp":"2026-02-28T15:42:49Z","request_id":"a1b2c3","method":"POST","path":"/api/v1/income","status":200,"duration_ms":12.34,"client_ip":"127.0.0.1"}
```

**日志级别控制：**

通过环境变量 `LOG_LEVEL` 设置（默认 `INFO`）：

| 级别 | 内容 |
|------|------|
| DEBUG | 每条 SQL 语句及耗时 |
| INFO | HTTP 请求、所有业务操作（收入、消费、结算等） |
| WARNING | 登录失败、结算锁竞争、违约升级 |
| ERROR | 未捕获异常（含完整 stack trace） |

**查看日志：**

```bash
# 开发环境（直接输出到终端）
LOG_LEVEL=DEBUG uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 生产环境（通过 journald）
journalctl -u fambank -f
journalctl -u fambank --since "1 hour ago" -o cat | jq .
```

**接入 CLS（腾讯云日志服务）：**

日志格式为标准 JSON Lines，安装 LogListener 后配置 JSON 提取模式即可自动解析所有字段。`request_id` 支持跨请求链路追踪。

## 生产部署

### 一、服务器初始化（一次性）

以下步骤在你的 Linux 服务器（云主机、VPS 等）上执行。

#### 1. 安装基础依赖

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y mysql-server nodejs npm git curl

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 建数据库

```bash
sudo mysql <<'SQL'
CREATE DATABASE IF NOT EXISTS fambank CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'fambank'@'localhost' IDENTIFIED BY '<你的强密码>';
GRANT ALL PRIVILEGES ON fambank.* TO 'fambank'@'localhost';
FLUSH PRIVILEGES;
SQL
```

#### 3. 拉代码、配环境、建表

```bash
sudo git clone <你的仓库地址> /opt/fambank
cd /opt/fambank

# 从模板创建 .env
sudo cp backend/.env.example backend/.env
sudo nano backend/.env
```

`.env` 中需要修改：

```bash
DB_PASSWORD=<你的强密码>
JWT_SECRET_KEY=<随机密钥>
# 生成方式: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

建表和导入种子数据：

```bash
mysql -u fambank -p fambank < backend/app/migrations/init.sql
mysql -u fambank -p fambank < backend/app/migrations/triggers.sql
mysql -u fambank -p fambank < backend/app/migrations/seed.sql
```

#### 4. 安装依赖、构建前端、启动服务

```bash
cd /opt/fambank/backend && uv sync && cd ..
cd /opt/fambank/frontend && npm ci && npm run build && cd ..

# 注册 systemd 服务并启动
sudo bash deploy/setup.sh
```

验证服务是否正常：

```bash
curl http://localhost:8000/api/v1/health
# 应返回 {"status":"ok","version":"0.1.0"}
```

#### systemd 服务说明

`deploy/setup.sh` 会注册一个 systemd 服务，配置如下：

- 以 `fambank` 系统用户运行（非 root）
- 环境变量从 `/opt/fambank/backend/.env` 读取
- 进程崩溃后 5 秒自动重启（`Restart=on-failure`）
- 60 秒内最多重启 5 次，超出后停止尝试
- 安全加固：`NoNewPrivileges=true`、`ProtectSystem=strict`
- 日志输出到 journald

```bash
# 常用命令
systemctl status fambank      # 查看状态
systemctl restart fambank     # 重启
journalctl -u fambank -f      # 实时日志
```

### 二、生成部署用 SSH 密钥（一次性）

CI/CD 需要一个专用密钥来 SSH 登录服务器。**在你本机执行**（不是服务器上）：

```bash
ssh-keygen -t ed25519 -C "fambank-deploy" -f ~/.ssh/fambank_deploy -N ""
```

生成两个文件：

| 文件 | 用途 |
|------|------|
| `~/.ssh/fambank_deploy` | 私钥 → 填入 GitHub Secrets |
| `~/.ssh/fambank_deploy.pub` | 公钥 → 放到服务器 |

**把公钥加到服务器的 authorized_keys**：

```bash
# 将 <SSH_USER> 和 <SSH_HOST> 替换为你的用户名和服务器 IP
ssh <SSH_USER>@<SSH_HOST> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys" < ~/.ssh/fambank_deploy.pub
```

**允许部署用户免密重启服务**（在服务器上执行）：

```bash
sudo visudo
# 在文件末尾加一行（将 ubuntu 替换为你的 SSH_USER）：
# ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart fambank
```

### 三、配置 GitHub Secrets

进入 GitHub 仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

逐个添加：

| Name | Value | 说明 |
|------|-------|------|
| `SSH_HOST` | `你的服务器IP` | 公网 IP 或域名 |
| `SSH_USER` | `ubuntu` | SSH 登录用户名 |
| `SSH_PRIVATE_KEY` | 私钥文件全部内容 | `cat ~/.ssh/fambank_deploy` 的输出，包括 BEGIN/END 行 |
| `SSH_PORT` | `22` | SSH 端口，默认 22 可不填 |

### 四、CI/CD 工作流程

配置完成后，推送代码即自动触发。

**test job**（每次 push / PR 都跑）：

```
checkout → 启动临时 MySQL 8.0 容器
→ uv sync → ruff check（lint）→ pytest（124 个测试）
→ npm ci → npm run build（前端编译检查）
```

**deploy job**（仅 push main 且 test 通过）：

```
SSH 到服务器 → git pull origin main
→ uv sync → npm ci && npm run build
→ systemctl restart fambank
→ 等待 3 秒 → curl 健康检查（失败则报错）
```

**验证方式**：推一次代码到 main，到仓库 **Actions** 页签查看：

- test job 绿色 → lint + 测试 + 构建全部通过
- deploy job 绿色 → 服务器已自动更新并重启

PR 只跑 test 不触发部署。

## 设计原则

- **金额精度**：所有金额以「分」（cents）为单位在后端和数据库中流转，API 层自动进行元/分转换
- **不可篡改审计**：transaction_log 表通过数据库触发器禁止 UPDATE 和 DELETE
- **原子结算**：结算 SOP 使用 MySQL advisory lock 防止并发
- **角色隔离**：家长和孩子有不同的操作权限
- **隐私保护**：所有密码/密钥通过环境变量配置，敏感文件不入库
