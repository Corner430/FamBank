# Quickstart: FamBank 家庭内部银行

## Prerequisites

- Python 3.12+
- uv (Python package manager)
- Node.js 18+
- MySQL 8.0+

## Setup

```bash
# 1. Clone
git clone <repo-url> fambank && cd fambank

# 2. Backend
cd backend
uv sync                     # install dependencies from pyproject.toml
cp .env.example .env        # configure MySQL connection
uv run python -m app.database --init  # create tables

# 3. Frontend
cd ../frontend
npm install
npm run build               # build for production

# 4. Start
cd ../backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Open
# Browser: http://localhost:8000
```

## First Use

1. **首次启动**时系统提示设置甲方管理密码和乙方 PIN 码
2. **甲方登录** → 使用管理密码
3. **乙方登录** → 使用 PIN 码

## Core Workflow

```
1. 录入收入 → 自动分流至 A/B/C
2. 管理愿望清单 → 备案标的、设定 P_active
3. 账户A消费 → 自由消费（不透支）
4. 账户B购买 → 清单标的（先扣本金后扣利息池）
5. 月度结算 → 甲方触发（C派息→B溢出→B计息→违约划转）
6. 查看记录 → 完整交易审计日志
```

## Verify Installation

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Expected: {"status":"ok","version":"0.1.0"}
```

## Backup

```bash
# Manual backup
mysqldump -u fambank -p fambank > backup-$(date +%Y%m%d).sql

# Restore
mysql -u fambank -p fambank < backup-20260228.sql
```

## Development

```bash
# Backend
cd backend
uv sync
uv run pytest               # run tests

# Frontend
cd frontend
npm install
npm run dev                 # dev server at localhost:5173
npm run test                # vitest
```
