# FamBank Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-28

## Active Technologies
- Python 3.12 (backend, managed by uv), TypeScript (frontend) (001-fambank-core)
- FastAPI, Pydantic, uvicorn, aiomysql/SQLAlchemy, Vue 3, Vite (001-fambank-core)
- MySQL 8.0 (InnoDB), monetary values as BIGINT cents (001-fambank-core)
- pytest (backend), Vitest (frontend) (001-fambank-core)

## Project Structure

```text
backend/
  app/
    main.py, auth.py, database.py
    models/, services/, api/, schemas/
  tests/
    unit/, integration/, conftest.py
  pyproject.toml, uv.lock

frontend/
  src/
    pages/, components/, services/, router/
  package.json, vite.config.ts
```

## Commands

```bash
# Backend
cd backend && uv sync && uv run pytest
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev
npm run build
```

## Code Style

- Python: ruff (lint + format)
- TypeScript: eslint + prettier
- All monetary values: BIGINT cents (DB), Decimal (Python), string (JSON)
- Every service function MUST create Transaction records with charter_clause reference

## Recent Changes
- 001-fambank-core: Python 3.12 + FastAPI + MySQL 8.0 + Vue 3 + uv

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
