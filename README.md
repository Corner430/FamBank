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

## 技术栈

**后端：** Python 3.12+ / FastAPI / SQLAlchemy (async) / aiomysql / MySQL 8.0

**前端：** Vue 3 / TypeScript / Vite / Vue Router

## 快速部署

### 前置要求

- Python 3.12+（推荐用 [uv](https://github.com/astral-sh/uv) 管理）
- Node.js 18+（仅构建前端时需要，部署后不需要）
- MySQL 8.0+（本地或云服务器均可）

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

### 3. 配置数据库连接

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```bash
# 本地数据库（默认值，无需改动）
DB_HOST=localhost
DB_PORT=3306
DB_USER=fambank
DB_PASSWORD=fambank
DB_NAME=fambank

# 云数据库示例
# DB_HOST=rm-xxx.mysql.rds.aliyuncs.com
# DB_PORT=3306
# DB_USER=fambank
# DB_PASSWORD=你的密码
# DB_NAME=fambank

# 也可以直接写完整连接字符串（优先级高于拆分字段）
# DATABASE_URL=mysql+aiomysql://user:pass@host:3306/fambank
```

### 4. 初始化数据库表和种子数据

```bash
# 本地
mysql -u fambank -pfambank fambank < backend/app/migrations/init.sql
mysql -u fambank -pfambank fambank < backend/app/migrations/triggers.sql
mysql -u fambank -pfambank fambank < backend/app/migrations/seed.sql

# 云数据库
mysql -h 你的主机 -P 3306 -u fambank -p fambank < backend/app/migrations/init.sql
mysql -h 你的主机 -P 3306 -u fambank -p fambank < backend/app/migrations/triggers.sql
mysql -h 你的主机 -P 3306 -u fambank -p fambank < backend/app/migrations/seed.sql
```

### 5. 构建前端

```bash
cd frontend
npm install && npm run build
cd ..
```

构建产物在 `frontend/dist/`，后端会自动托管，无需单独部署前端。

### 6. 启动服务

```bash
cd backend
uv sync                    # 安装依赖（也可用 pip install -e .）
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 **http://localhost:8000** 即可使用（API + 前端都在这个端口）。

### 7. 初始化系统

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

### C 牛马金 - 长期储蓄

- 每月结算时自动计息（年化 5%，按月派息至 A）
- 18 岁前锁定，提前赎回需扣 10% 手续费（家长审批）

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
cd backend
source .venv/bin/activate

# 创建测试数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS fambank_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL ON fambank_test.* TO 'fambank'@'localhost';"

# 运行全部 96 个测试
python -m pytest tests/ -v
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

### systemd 服务（自动重启）

```bash
# 一键部署（需要 root 权限）
sudo bash deploy/setup.sh
```

服务配置：
- 进程崩溃后 5 秒自动重启（`Restart=on-failure`）
- 60 秒内最多重启 5 次，超出后停止尝试
- 日志输出到 journald

```bash
# 常用命令
systemctl status fambank      # 查看状态
systemctl restart fambank     # 重启
journalctl -u fambank -f      # 实时日志
```

### CI/CD（GitHub Actions）

推送到 `main` 分支时自动触发：

1. **test job**（每次 push / PR）：MySQL 8.0 service container → ruff lint → pytest → 前端 build
2. **deploy job**（仅 main push 且 test 通过）：SSH 到服务器 → git pull → 依赖安装 → 前端构建 → 重启服务 → 健康检查

需要在 GitHub 仓库配置以下 Secrets：

| Secret | 说明 |
|--------|------|
| `SSH_HOST` | 服务器 IP |
| `SSH_USER` | SSH 用户名 |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `SSH_PORT` | SSH 端口（可选，默认 22） |

## 设计原则

- **金额精度**：所有金额以「分」（cents）为单位在后端和数据库中流转，API 层自动进行元/分转换
- **不可篡改审计**：transaction_log 表通过数据库触发器禁止 UPDATE 和 DELETE
- **原子结算**：结算 SOP 使用 MySQL advisory lock 防止并发
- **角色隔离**：家长和孩子有不同的操作权限
