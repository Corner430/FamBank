# Implementation Plan: FamBank 家庭内部银行核心系统

**Branch**: `001-fambank-core` | **Date**: 2026-02-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fambank-core/spec.md`

## Summary

基于《家庭内部银行·分层资产管理章程 V3.2》实现完整的家庭内部银行 Web 应用。系统实现三账户（A零钱宝/B梦想金/C牛马金）分层管理，支持收入自动分流、分层利率计息、愿望清单驱动的购买消费、原子化月度结算、违约处理和完整审计追溯。

技术方案：Python FastAPI 后端（uv 管理依赖）+ Vue 3 前端 + MySQL 存储，全链路定点小数（整数分存储 + Python Decimal 运算），直接部署。

## Technical Context

**Language/Version**: Python 3.12 (backend, managed by uv), TypeScript (frontend)
**Primary Dependencies**: FastAPI, Pydantic, uvicorn, aiomysql/SQLAlchemy, Vue 3, Vite
**Storage**: MySQL 8.0 (InnoDB), monetary values as BIGINT cents
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Any Linux/macOS host with MySQL
**Project Type**: web-service (responsive web app)
**Performance Goals**: <500ms page load, <200ms API response (single-family, 1-3 concurrent users)
**Constraints**: 金额精确到分(0.01元), 结算原子性, 审计日志仅追加
**Scale/Scope**: 单家庭（1甲方+1乙方）, ~6 pages, ~15 API endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Gate | Status |
|---|-----------|------|--------|
| I | 章程即法 | 所有业务逻辑与章程条款一一对应 | PASS — 24条FR逐条映射章程 |
| II | 金额精确 | 定点小数，精确到分，可追溯 | PASS — 整数分存储(BIGINT) + Python Decimal + Pydantic 校验 |
| III | 分层账户隔离 | A/B/C数据隔离，仅允许章程路径 | PASS — Account表独立记录，Transaction表强制source/target约束 |
| IV | 结算原子性 | 四步SOP不可分割，失败回滚 | PASS — MySQL InnoDB 事务 |
| V | 审计可追溯 | 完整日志，仅追加 | PASS — Transaction表 + MySQL trigger禁止UPDATE/DELETE |
| VI | 测试覆盖 | 公式单元测试+边界用例，SOP集成测试 | PASS — pytest参数化测试策略 |
| VII | 简洁优先 | 只实现章程要求，YAGNI | PASS — 直接部署，uv管理依赖，无多余抽象 |

**Post-Design Re-check**: All gates remain PASS after Phase 1 design. No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/001-fambank-core/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: setup guide
├── contracts/
│   └── api.md           # Phase 1: REST API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py              # FastAPI app entry, CORS, static mount
│   ├── auth.py              # PIN/password auth, session management
│   ├── database.py          # MySQL connection, migrations
│   ├── models/
│   │   ├── account.py       # Account entity (A/B/C)
│   │   ├── transaction.py   # Transaction (audit log)
│   │   ├── wishlist.py      # WishList + WishItem
│   │   ├── settlement.py    # Settlement record
│   │   ├── violation.py     # Violation record
│   │   ├── config.py        # Config + Announcement
│   │   ├── debt.py          # Debt record
│   │   └── escrow.py        # Escrow (B suspend buffer)
│   ├── services/
│   │   ├── income.py        # Income split logic (charter §2)
│   │   ├── settlement.py    # 4-step SOP (charter appendix)
│   │   ├── interest.py      # Tiered interest calc (charter §4.5)
│   │   ├── overflow.py      # B overflow logic (charter §4.4)
│   │   ├── purchase.py      # B purchase + compliance (charter §4.6)
│   │   ├── spending.py      # A free spending (charter §3)
│   │   ├── violation.py     # Violation + penalty (charter §7)
│   │   ├── redemption.py    # C emergency redemption (charter §5)
│   │   ├── wishlist.py      # Wish list management (charter §4.2-4.3)
│   │   └── config.py        # Config + announcement (charter §8)
│   ├── api/
│   │   ├── auth.py          # Auth endpoints
│   │   ├── income.py        # POST /income
│   │   ├── accounts.py      # GET /accounts, spending, purchase
│   │   ├── wishlist.py      # Wish list CRUD
│   │   ├── settlement.py    # POST /settlement, GET /settlements
│   │   ├── violations.py    # POST /violations
│   │   ├── redemption.py    # Redemption request/approve
│   │   ├── transactions.py  # GET /transactions
│   │   └── config.py        # GET/POST config
│   └── schemas/
│       └── *.py             # Pydantic request/response models
├── tests/
│   ├── unit/
│   │   ├── test_income_split.py      # 分流公式 + 尾差
│   │   ├── test_interest_calc.py     # 分层利率边界
│   │   ├── test_overflow.py          # 溢出计算
│   │   ├── test_penalty.py           # 罚金公式
│   │   └── test_redemption_fee.py    # 赎回违约金
│   ├── integration/
│   │   ├── test_settlement_sop.py    # 四步结算完整流程
│   │   ├── test_settlement_rollback.py # 结算回滚
│   │   ├── test_audit_immutability.py  # 审计日志不可篡改
│   │   └── test_fund_conservation.py   # 资金守恒
│   └── conftest.py
├── pyproject.toml               # uv project config
└── uv.lock                      # uv lock file

frontend/
├── src/
│   ├── App.vue
│   ├── main.ts
│   ├── router/
│   │   └── index.ts
│   ├── pages/
│   │   ├── LoginPage.vue        # PIN/密码登录
│   │   ├── DashboardPage.vue    # 账户总览
│   │   ├── IncomePage.vue       # 录入收入
│   │   ├── WishListPage.vue     # 愿望清单管理
│   │   ├── TransactionsPage.vue # 交易记录查询
│   │   └── SettlementPage.vue   # 月度结算（甲方）
│   ├── components/
│   │   ├── AccountCard.vue      # 账户余额卡片
│   │   ├── TransactionList.vue  # 交易记录列表
│   │   └── SettlementReport.vue # 结算报告
│   └── services/
│       └── api.ts               # API client (fetch wrapper)
├── tests/
│   └── *.test.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

**Structure Decision**: Web application 结构（backend + frontend 分离）。FastAPI 后端提供 REST API 并在生产环境托管前端静态文件。Python 依赖通过 uv 管理（pyproject.toml + uv.lock）。MySQL 作为独立数据库服务。

## Complexity Tracking

> No Constitution Check violations. No complexity justifications needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | | |
