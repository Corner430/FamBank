# Implementation Plan: FamBank 多家庭多租户产品化

**Branch**: `002-multi-tenant-platform` | **Date**: 2026-03-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-multi-tenant-platform/spec.md`

## Summary

将 FamBank 从单家庭工具演进为多家庭 To C 平台。核心变更：手机号+短信验证码认证（替代 PIN）、家庭创建与邀请码机制、每个孩子独立 A/B/C 账户、family_id 服务层强制数据隔离、家长聚合 Dashboard。所有现有业务功能（入账分流、结算、愿望清单、购买、违约、赎回、配置）保持逻辑不变，适配到多租户维度。

## Technical Context

**Language/Version**: Python 3.12 (backend, managed by uv), TypeScript (frontend)
**Primary Dependencies**: FastAPI, Pydantic, uvicorn, aiomysql/SQLAlchemy, PyJWT, Vue 3, Vue Router, Vite
**Storage**: MySQL 8.0 (InnoDB), monetary values as BIGINT cents
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Linux server (systemd), Web browser (responsive SPA)
**Project Type**: Web application (FastAPI backend + Vue 3 SPA frontend)
**Performance Goals**: Standard web app — page loads < 2s, API responses < 500ms
**Constraints**: Dev SMS uses fixed code 123456; production uses Tencent Cloud SMS
**Scale/Scope**: MVP targets ~100 families, ~10 children per family max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. 章程即法 | ✅ PASS | 所有业务逻辑保持不变，章程作为模板提供给每个家庭 |
| II. 金额精确 | ✅ PASS | 金额计算逻辑不修改，仍为 BIGINT cents + Decimal |
| III. 分层账户隔离 | ✅ PASS | 每个孩子独立 A/B/C，`user_id` FK 确保数据隔离 |
| IV. 结算原子性 | ✅ PASS | 每个孩子独立原子结算（per-child advisory lock） |
| V. 审计可追溯 | ✅ PASS | TransactionLog 加 family_id + user_id，trigger 不变 |
| VI. 测试覆盖 | ✅ PASS | 原有测试 + 新增多租户隔离测试、认证测试 |
| VII. 简洁优先 | ✅ PASS | 仅增加产品化必需的认证/租户/家庭基础设施 |
| VIII. 租户隔离 | ✅ PASS | family_id 服务层强制注入，TenantContext 依赖 |
| IX. 认证与身份 | ✅ PASS | 手机号+验证码，JWT 携带 user_id/family_id/role |

## Project Structure

### Documentation (this feature)

```text
specs/002-multi-tenant-platform/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
  app/
    main.py                         # MODIFY: remove PIN routes, add new routes
    auth.py                         # REWRITE: phone+SMS JWT (replace PIN-based)
    database.py                     # NO CHANGE (002 migration run manually via mysql CLI)
    middleware/
      request_logging.py            # MODIFY: add family_id/user_id to log context
    models/
      __init__.py                   # MODIFY: export new models
      base.py                       # NO CHANGE
      user.py                       # MODIFY: add phone, family_id; drop pin_hash, unique(role)
      account.py                    # MODIFY: add family_id, user_id; change unique constraint
      config.py                     # MODIFY: add family_id to Config and Announcement
      settlement.py                 # MODIFY: add family_id, user_id; change unique constraint
      transaction.py                # MODIFY: add family_id, user_id
      violation.py                  # MODIFY: add family_id, user_id
      debt.py                       # MODIFY: add family_id, user_id
      escrow.py                     # MODIFY: add family_id, user_id
      wishlist.py                   # MODIFY: add family_id, user_id
      redemption_request.py         # MODIFY: add family_id
      family.py                     # NEW: Family model
      invitation.py                 # NEW: Invitation model
      sms_code.py                   # NEW: SmsCode model
      refresh_token.py              # NEW: RefreshToken model
    schemas/
      auth.py                       # REWRITE: phone+code schemas (replace PIN)
      common.py                     # NO CHANGE
      family.py                     # NEW: family/invitation schemas
      income.py                     # MODIFY: add child_id
      settlement.py                 # MODIFY: per-child results
      (others)                      # MODIFY: add child_id where needed
    services/
      auth.py                       # NEW: SMS code send/verify, token management
      family.py                     # NEW: create family, invite, join
      sms.py                        # NEW: SMS provider abstraction (dev mock + Tencent)
      tenant.py                     # NEW: TenantContext dependency
      income.py                     # MODIFY: accept user_id, filter by family
      settlement.py                 # MODIFY: loop over children, per-child atomic
      config.py                     # MODIFY: filter by family_id
      spending.py                   # MODIFY: accept user_id, filter by family
      purchase.py                   # MODIFY: accept user_id, filter by family
      violation.py                  # MODIFY: accept user_id, filter by family
      redemption.py                 # MODIFY: accept user_id, filter by family
      wishlist.py                   # MODIFY: accept user_id, filter by family
      transaction.py                # MODIFY: filter by family_id + user_id
      escrow.py                     # MODIFY: filter by family_id + user_id
    api/
      deps.py                       # REWRITE: TenantContext + role deps (replace PIN auth)
      auth.py                       # REWRITE: send-code, verify-code, refresh
      family.py                     # NEW: family CRUD, invitations, join, dashboard
      accounts.py                   # MODIFY: child_id injection
      income.py                     # MODIFY: child_id parameter
      settlement.py                 # MODIFY: per-family settlement
      transactions.py               # MODIFY: child_id filtering
      violations.py                 # MODIFY: child_id parameter
      wishlist.py                   # MODIFY: child_id parameter
      redemption.py                 # MODIFY: child_id parameter
      config.py                     # MODIFY: family_id filtering
    migrations/
      init.sql                      # NO CHANGE (001 baseline)
      seed.sql                      # MODIFY: no longer auto-seed accounts/config (done per-family)
      triggers.sql                  # NO CHANGE
      002_multi_tenant.sql          # NEW: schema migration

  tests/
    unit/                           # MODIFY: update for multi-tenant
    integration/                    # MODIFY: update for multi-tenant
    conftest.py                     # MODIFY: test fixtures for families/children

frontend/
  src/
    services/
      api.ts                        # MODIFY: new auth flow, family APIs, child_id params
    router/
      index.ts                      # MODIFY: add onboarding, dashboard, child routes
    pages/
      LoginPage.vue                 # REWRITE: phone+SMS code UI (replace PIN)
      OnboardingPage.vue            # NEW: create/join family
      DashboardPage.vue             # REWRITE: parent aggregated view
      ChildDetailPage.vue           # NEW: parent viewing specific child (wraps existing views)
      IncomePage.vue                 # MODIFY: child selector for parent
      SettlementPage.vue            # MODIFY: per-child results display
      SettingsPage.vue              # REWRITE: remove PIN management, add family/invitation management
      (others)                      # MINOR CHANGES: child context awareness
    components/
      AccountCard.vue               # NO CHANGE
      ChildSelector.vue             # NEW: child picker for parent operations
      FamilyMemberList.vue          # NEW: family member display
      InvitationManager.vue         # NEW: invite code generation/management
      TransactionList.vue           # NO CHANGE
      SettlementReport.vue          # NO CHANGE
```

**Structure Decision**: Existing backend/ + frontend/ structure from 001-fambank-core is retained. New files added within existing directory hierarchy. No new top-level directories needed.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|-------------------------------------|
| TenantContext dependency injection | Constitution VIII mandates service-layer forced filtering | Manual family_id passing in each query is error-prone and violates "architecturally impossible" requirement |
| Refresh token in DB | Need to invalidate when user joins family (family_id in JWT changes) | Stateless refresh tokens can't be invalidated on family join |
| Per-child advisory locks in settlement | FR-017 requires independent child settlement failure isolation | Single global lock would cause one child's failure to roll back all |
| SMS provider abstraction (dev mock + Tencent) | Dev can't send real SMS; prod needs Tencent Cloud | Hard-coding either mode would require code changes to switch |
