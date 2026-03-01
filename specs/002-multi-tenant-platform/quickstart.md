# Quickstart: FamBank 多家庭多租户产品化

**Branch**: `002-multi-tenant-platform`
**Date**: 2026-03-01

## Prerequisites

- Python 3.12 + uv (backend)
- Node.js 18+ + npm (frontend)
- MySQL 8.0 running locally

## Setup

```bash
# 1. Backend
cd backend
uv sync
cp .env.example .env   # 配置 DATABASE_URL, JWT_SECRET_KEY, SMS_MODE=dev

# 2. Run migration (after 001 init.sql)
mysql -u root fambank < app/migrations/002_multi_tenant.sql

# 3. Start backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend
cd ../frontend
npm install
npm run dev
```

## Dev Mode SMS

开发模式下 (`SMS_MODE=dev` in .env)，所有手机号的验证码固定为 `123456`，不发送真实短信。

## Quick Test Flow

1. 打开 http://localhost:5173
2. 输入手机号 `13800138000`，点击获取验证码
3. 输入 `123456` 完成注册
4. 在 onboarding 页面创建家庭"测试家庭"
5. 生成邀请码（角色: child，名称: 小明）
6. 新浏览器窗口注册 `13800138001`，使用邀请码加入
7. 以家长身份为小明录入收入，验证分流

## Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string | `mysql+aiomysql://root@localhost/fambank` |
| `JWT_SECRET_KEY` | JWT signing secret | (required in production) |
| `JWT_ACCESS_EXPIRE_HOURS` | Access token lifetime | `24` |
| `JWT_REFRESH_EXPIRE_DAYS` | Refresh token lifetime | `30` |
| `SMS_MODE` | `dev` (fake) or `prod` (Tencent Cloud) | `dev` |
| `TENCENT_SMS_SECRET_ID` | Tencent Cloud SMS Secret ID | (prod only) |
| `TENCENT_SMS_SECRET_KEY` | Tencent Cloud SMS Secret Key | (prod only) |
| `TENCENT_SMS_SDK_APP_ID` | Tencent Cloud SMS App ID | (prod only) |
| `TENCENT_SMS_TEMPLATE_ID` | Tencent Cloud SMS Template ID | (prod only) |
| `TENCENT_SMS_SIGN_NAME` | Tencent Cloud SMS Sign Name | (prod only) |
