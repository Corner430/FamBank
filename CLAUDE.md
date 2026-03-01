# FamBank Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-28

## Active Technologies
- Python 3.12 (backend, managed by uv), TypeScript (frontend) (001-fambank-core)
- FastAPI, Pydantic, uvicorn, aiomysql/SQLAlchemy, Vue 3, Vite (001-fambank-core)
- MySQL 8.0 (InnoDB), monetary values as BIGINT cents (001-fambank-core)
- structlog: 结构化 JSON 日志，所有 service 和 HTTP 请求均覆盖
- pytest (backend), Vitest (frontend) (001-fambank-core)
- systemd (进程管理), GitHub Actions (CI/CD)

## Project Structure

```text
backend/
  app/
    main.py, auth.py, database.py, logging_config.py
    middleware/          # RequestLoggingMiddleware
    models/, services/, api/, schemas/
  tests/
    unit/, integration/, conftest.py
  pyproject.toml, uv.lock

frontend/
  src/
    pages/, components/, services/, router/
  package.json, vite.config.ts

deploy/
  fambank.service, setup.sh

.github/workflows/
  ci-deploy.yml
```

## Commands

```bash
# Backend
cd backend && uv sync && uv run pytest
uv run ruff check .
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev
npm run build

# Deploy
sudo bash deploy/setup.sh          # 首次部署
sudo systemctl restart fambank      # 重启服务
journalctl -u fambank -f            # 查看日志
```

## Code Style

- Python: ruff (lint + format), ruff 0 告警才可提交
- TypeScript: eslint + prettier
- All monetary values: BIGINT cents (DB), Decimal (Python), string (JSON)
- Every service function MUST create Transaction records with charter_clause reference
- 日志: 所有 service 文件顶部 `logger = structlog.get_logger("模块名")`，业务操作必须有 INFO 日志，JSON 格式输出
- 环境变量 LOG_LEVEL 控制日志级别（默认 INFO）
- CI/CD: 推送 main 分支自动触发 test + deploy

## Recent Changes
- 001-fambank-core: Python 3.12 + FastAPI + MySQL 8.0 + Vue 3 + uv
- structlog 结构化 JSON 日志，覆盖全部 service 和 HTTP 请求
- systemd 服务（自动重启）+ GitHub Actions CI/CD（test + deploy → main）
- C 赎回审批持久化：新增 redemption_request 表，request/approve/reject 全部写库，前端从 API 加载 pending 列表
- JWT_SECRET_KEY 改为环境变量配置（auth.py），生产环境必须在 .env 中设置

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
