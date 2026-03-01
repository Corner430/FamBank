# Tasks: FamBank 多家庭多租户产品化

**Input**: Design documents from `/specs/002-multi-tenant-platform/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted. Existing tests will be updated as part of the Polish phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration, new models, and core infrastructure that all stories depend on

- [x] T001 Create database migration file `backend/app/migrations/002_multi_tenant.sql` — new tables (family, invitation, sms_code, refresh_token), ALTER existing tables to add family_id/user_id columns, drop pin_hash from user, adjust unique constraints, add indexes per data-model.md. Note: `backend/app/database.py` does not need modification — migration is run manually via mysql CLI per quickstart.md
- [x] T002 [P] Create Family model in `backend/app/models/family.py` — id, name, created_by (FK user), created_at
- [x] T003 [P] Create Invitation model in `backend/app/models/invitation.py` — id, family_id (FK), code (UNIQUE VARCHAR 8), target_role (ENUM parent/child), target_name, status (ENUM pending/used/revoked/expired), created_by (FK), used_by (FK nullable), expires_at, created_at
- [x] T004 [P] Create SmsCode model in `backend/app/models/sms_code.py` — id, phone, code, expires_at, is_used, attempts, created_at; index on (phone, created_at DESC)
- [x] T005 [P] Create RefreshToken model in `backend/app/models/refresh_token.py` — id, user_id (FK), token_hash (UNIQUE), expires_at, is_revoked, created_at
- [x] T006 Modify User model in `backend/app/models/user.py` — ADD phone (VARCHAR 11, UNIQUE, NOT NULL), ADD family_id (FK family, nullable), DROP pin_hash, MODIFY role (remove UNIQUE constraint, allow NULL)
- [x] T007 [P] Modify Account model in `backend/app/models/account.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL), change unique constraint from UNIQUE(account_type) to UNIQUE(user_id, account_type)
- [x] T008 [P] Modify Config model in `backend/app/models/config.py` — ADD family_id (FK, NOT NULL) to both Config and Announcement; add index on (family_id, key, effective_from)
- [x] T009 [P] Modify Settlement model in `backend/app/models/settlement.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL), change unique from UNIQUE(settlement_date) to UNIQUE(user_id, settlement_date)
- [x] T010 [P] Modify TransactionLog model in `backend/app/models/transaction.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL)
- [x] T011 [P] Modify Violation model in `backend/app/models/violation.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL)
- [x] T012 [P] Modify Debt model in `backend/app/models/debt.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL)
- [x] T013 [P] Modify Escrow model in `backend/app/models/escrow.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL)
- [x] T014 [P] Modify WishList model in `backend/app/models/wishlist.py` — ADD family_id (FK, NOT NULL), ADD user_id (FK, NOT NULL)
- [x] T015 [P] Modify RedemptionRequest model in `backend/app/models/redemption_request.py` — ADD family_id (FK, NOT NULL)
- [x] T016 Update models `__init__.py` in `backend/app/models/__init__.py` — export Family, Invitation, SmsCode, RefreshToken
- [x] T017 Modify seed data in `backend/app/migrations/seed.sql` — remove auto-seed of accounts/config (now done per-family at creation time)

**Checkpoint**: All models reflect the multi-tenant data model. Migration script ready to run.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented — TenantContext, auth rewrite, API dependency injection

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T018 Create SMS provider abstraction in `backend/app/services/sms.py` — interface with send_code(phone) method; DevSmsProvider (returns fixed 123456, no network) and TencentSmsProvider (calls Tencent Cloud SMS API); select based on SMS_MODE env var
- [x] T019 Create TenantContext service in `backend/app/services/tenant.py` — dependency injection class that extracts family_id, user_id, role from JWT; provides get_family_id(), get_user_id(), get_role(), require_parent(), require_family() helpers; raises 403 on violations
- [x] T020 Rewrite auth module in `backend/app/auth.py` — remove all PIN-based logic; implement JWT encode/decode with claims {user_id, family_id (nullable), role (nullable)}; access token 24h expiry, refresh token 30d expiry; use JWT_SECRET_KEY from env
- [x] T021 Rewrite API dependencies in `backend/app/api/deps.py` — replace PIN-based auth deps with: get_current_user (JWT decode), require_family (must have family_id), require_parent (must be parent role), get_tenant_context (returns TenantContext), resolve_child_id (parent: from param, child: from JWT)
- [x] T022 Rewrite auth schemas in `backend/app/schemas/auth.py` — SendCodeRequest(phone), VerifyCodeResponse(access_token, refresh_token, user, is_new_user), RefreshRequest(refresh_token), RefreshResponse(access_token, refresh_token), UserInfo(id, phone, family_id, role, name)
- [x] T023 [P] Create family schemas in `backend/app/schemas/family.py` — CreateFamilyRequest(name, creator_name: Optional[str] = None), FamilyResponse(family, access_token), FamilyDetailResponse(family, members), CreateInvitationRequest(target_role, target_name), InvitationResponse, JoinFamilyRequest(code), JoinFamilyResponse(family, role, name, access_token), DashboardResponse(family_name, total_assets, children[])
- [x] T024 Modify request logging middleware in `backend/app/middleware/request_logging.py` — add family_id and user_id to structlog context from JWT when available
- [x] T025 Update `backend/app/main.py` — remove old PIN auth routes; add new auth routes (send-code, verify-code, refresh); add family routes; update CORS and middleware; ensure all business routers use new auth deps; **all business routes MUST use require_family dependency to enforce FR-006a** (no-family users blocked from all business APIs)

**Checkpoint**: Foundation ready — JWT auth works, TenantContext injectable, API deps available, SMS provider ready

---

## Phase 3: User Story 1 — 手机号注册与登录 (Priority: P1) MVP

**Goal**: Users can register/login with phone+SMS code, receive JWT tokens, refresh tokens

**Independent Test**: Send code to phone → verify code → get tokens → refresh token → verify user created

**FRs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-006b

### Implementation for User Story 1

- [x] T026 [US1] Create auth service in `backend/app/services/auth.py` — send_code(phone): validate phone format (regex `^1\d{10}$`), check 60s rate limit, check 15min lockout (5 failed attempts), if valid unexpired code already exists and >60s since creation then invalidate old code and generate new one, generate code (dev: 123456, prod: random 6-digit), store SmsCode record, call SMS provider; verify_code(phone, code): find latest unexpired SmsCode, check attempts < 5, verify code match, mark used, find-or-create User, generate JWT access+refresh tokens, store RefreshToken; refresh_token(token): validate hash in DB, check not revoked/expired, issue new pair, revoke old
- [x] T027 [US1] Rewrite auth API routes in `backend/app/api/auth.py` — POST /auth/send-code (calls auth service send_code, returns 200/429); POST /auth/verify-code (calls verify_code, returns 200 with tokens+user+is_new_user / 401); POST /auth/refresh (calls refresh_token, returns 200 / 401)
- [x] T028 [US1] Rewrite login frontend in `frontend/src/pages/LoginPage.vue` — phone input with format validation (regex `^1\d{10}$`, show error on invalid format before submission), "获取验证码" button with 60s countdown, code input (6 digits), submit → call POST /auth/verify-code → store tokens in localStorage → redirect based on user.family_id (null → /onboarding, else → /dashboard or child home)
- [x] T029 [US1] Update API service in `frontend/src/services/api.ts` — add sendCode(phone), verifyCode(phone, code), refreshToken(token) methods; update axios interceptor to use Bearer JWT from localStorage; add 401 interceptor to attempt token refresh before logout

**Checkpoint**: Users can register and login via phone+SMS. JWT auth fully functional.

---

## Phase 4: User Story 2 — 创建家庭 (Priority: P1)

**Goal**: Logged-in user without a family can create one, becoming parent; family config auto-initialized

**Independent Test**: Login → create family "张家" → verify role=parent, config initialized with charter defaults

**FRs**: FR-007, FR-008, FR-009

### Implementation for User Story 2

- [x] T030 [US2] Create family service in `backend/app/services/family.py` — create_family(user_id, name, creator_name=None): check user has no family_id, create Family record, set user.family_id + user.role=parent + user.name=(creator_name if provided, else "家长"), initialize default Config rows (split ratios, interest rates, penalty multiplier, redemption fee per charter), return family + new JWT access token with updated claims
- [x] T031 [US2] Create family API routes (create + get) in `backend/app/api/family.py` — POST /family (require logged in + no family, accepts name + optional creator_name, calls create_family, returns 201 with family + new access_token); GET /family (require family, return family info + member list)
- [x] T032 [US2] Modify config service in `backend/app/services/config.py` — add init_default_config(family_id, db) to insert charter default values; update all config query methods to filter by family_id from TenantContext
- [x] T033 [US2] Create OnboardingPage in `frontend/src/pages/OnboardingPage.vue` — two-button gate: "创建家庭" (opens family name input + optional creator display name input + submit) and "输入邀请码" (opens code input + submit); no other navigation visible
- [x] T034 [US2] Update router in `frontend/src/router/index.ts` — add /onboarding route (OnboardingPage); add navigation guard: if user logged in but family_id is null, redirect to /onboarding; block all business routes for no-family users

**Checkpoint**: Users can create families. Config auto-initialized. Onboarding flow works.

---

## Phase 5: User Story 3 — 邀请成员加入家庭 (Priority: P1)

**Goal**: Parents generate invite codes, new users join with codes, children get A/B/C accounts auto-created

**Independent Test**: Parent creates invite (child, "小明") → new user joins with code → verify role=child, name="小明", 3 accounts created with balance 0

**FRs**: FR-010, FR-011, FR-012, FR-013

### Implementation for User Story 3

- [x] T035 [US3] Add invitation methods to family service in `backend/app/services/family.py` — create_invitation(family_id, created_by, target_role, target_name): generate 8-char code (uppercase alphanumeric, exclude O/0/I/1), set expires_at +7d, return Invitation; list_invitations(family_id): return all invitations for family; revoke_invitation(invitation_id, family_id): set status=revoked if pending; join_family(user_id, code): validate code (exists, pending, not expired), set user family_id/role/name from invitation, mark invitation used, if role=child create 3 Account records (A/B/C, balance=0), revoke all user's old refresh tokens, return family + new JWT
- [x] T036 [US3] Add invitation + join API routes in `backend/app/api/family.py` — POST /family/invitations (require parent, calls create_invitation, returns 201); GET /family/invitations (require parent, returns list); DELETE /family/invitations/{id} (require parent, calls revoke); POST /family/join (require logged in + no family, calls join_family, returns 200 with family + role + name + new access_token)
- [x] T037 [US3] Create InvitationManager component in `frontend/src/components/InvitationManager.vue` — form to generate invite (role selector, name input), list of existing invitations with status/code/expiry, revoke button for pending ones
- [x] T038 [US3] Create FamilyMemberList component in `frontend/src/components/FamilyMemberList.vue` — displays family members (name, role) fetched from GET /family
- [x] T039 [US3] Wire join-family flow in `frontend/src/pages/OnboardingPage.vue` — "输入邀请码" path: code input → POST /family/join → update stored JWT → redirect to appropriate home page
- [x] T040 [US3] Rewrite SettingsPage in `frontend/src/pages/SettingsPage.vue` — remove all PIN management from this page (definitive owner of SettingsPage PIN cleanup); add family info section (name, member list via FamilyMemberList), invitation management section (InvitationManager), logout button

**Checkpoint**: Full invite/join flow works. Children auto-get accounts. Settings page updated.

---

## Phase 6: User Story 8 — 租户数据隔离 (Priority: P1)

**Goal**: All data queries filtered by family_id at service layer; cross-family access impossible; child sees only own data

**Independent Test**: Create two families with data, attempt cross-family API calls → all rejected

**FRs**: FR-018, FR-019, FR-020, FR-021, FR-022

### Implementation for User Story 8

- [x] T041 [US8] Modify income service in `backend/app/services/income.py` — accept user_id (child) parameter; filter all queries by family_id from TenantContext; validate child belongs to family before operating; parent: use provided child_id, child: use self user_id
- [x] T042 [P] [US8] Modify transaction service in `backend/app/services/transaction.py` — filter all queries by family_id from TenantContext + optional user_id; add family_id and user_id to all new TransactionLog records
- [x] T043 [P] [US8] Modify spending service in `backend/app/services/spending.py` — accept user_id parameter; filter by family_id from TenantContext; validate child belongs to family
- [x] T044 [P] [US8] Modify purchase service in `backend/app/services/purchase.py` — accept user_id parameter; filter by family_id from TenantContext; validate child belongs to family
- [x] T045 [P] [US8] Modify violation service in `backend/app/services/violation.py` — accept user_id parameter; filter by family_id from TenantContext; validate child belongs to family
- [x] T046 [P] [US8] Modify redemption service in `backend/app/services/redemption.py` — accept user_id parameter; filter by family_id from TenantContext; validate child belongs to family
- [x] T047 [P] [US8] Modify wishlist service in `backend/app/services/wishlist.py` — accept user_id parameter; filter by family_id from TenantContext; validate child belongs to family
- [x] T048 [P] [US8] Modify escrow service in `backend/app/services/escrow.py` — filter by family_id + user_id from TenantContext

**Checkpoint**: All services enforce family_id filtering. Cross-family access impossible at service layer.

---

## Phase 7: User Story 4 — 多子女独立账户与入账 (Priority: P1)

**Goal**: Parent can record income for a specific child, funds split to that child's A/B/C only

**Independent Test**: Family with 2 children → record income for child A → verify only child A's accounts change, child B unchanged

**FRs**: FR-014, FR-015

**Depends on**: US8 (service-layer tenant filtering must be in place)

### Implementation for User Story 4

- [x] T049 [US4] Modify income schemas in `backend/app/schemas/income.py` — add child_id field to income request schema (required for parent)
- [x] T050 [US4] Modify income API route in `backend/app/api/income.py` — use resolve_child_id dep to determine target child; pass user_id to income service (builds on T041 service-layer changes); validate child belongs to family
- [x] T051 [US4] Modify accounts API route in `backend/app/api/accounts.py` — add child_id query param for parent; child auto-uses self; use resolve_child_id dep; pass user_id to service queries
- [x] T052 [US4] Create ChildSelector component in `frontend/src/components/ChildSelector.vue` — dropdown/picker showing family children (fetched from GET /family); emits selected child_id; auto-selects if only one child
- [x] T053 [US4] Modify IncomePage in `frontend/src/pages/IncomePage.vue` — add ChildSelector for parent role; include child_id in POST /income request; show child context in income history

**Checkpoint**: Multi-child income recording works. Each child's accounts independent.

---

## Phase 8: User Story 5 — 家长聚合 Dashboard (Priority: P2)

**Goal**: Parent sees aggregated view of all children's accounts; can drill into child detail

**Independent Test**: Family with 2 children with balances → parent sees dashboard with both summaries + total → click to detail page

**FRs**: FR-023, FR-024

### Implementation for User Story 5

- [x] T054 [US5] Add dashboard endpoint to family API in `backend/app/api/family.py` — GET /family/dashboard (require parent); query all children in family, for each child get A/B/C account balances, compute per-child total and family total_assets; return DashboardResponse
- [x] T055 [US5] Rewrite DashboardPage in `frontend/src/pages/DashboardPage.vue` — call GET /family/dashboard; display family_name + total_assets; render child cards (name, A/B/C balances, total); click child card → navigate to /child/:childId; empty state: "还没有孩子加入，请生成邀请码邀请成员"
- [x] T056 [US5] Create ChildDetailPage in `frontend/src/pages/ChildDetailPage.vue` — wrapper that sets child context from route param :childId; renders existing account views (AccountCard, TransactionList) with child_id param; back button to /dashboard
- [x] T057 [US5] Update router in `frontend/src/router/index.ts` — add /dashboard route (parent only); add /child/:childId route (parent only, ChildDetailPage); set /dashboard as parent's default home; navigation guard: parent → /dashboard, child → existing account page

**Checkpoint**: Parent dashboard functional. Child drill-down works.

---

## Phase 9: User Story 6 — 孩子视图（仅看自己） (Priority: P2)

**Goal**: Child user sees only own A/B/C accounts and transactions; no dashboard or sibling data

**Independent Test**: Login as child → see own accounts → attempt to access sibling data via URL → rejected

**FRs**: FR-021, FR-025

### Implementation for User Story 6

- [x] T058 [US6] Update router guards in `frontend/src/router/index.ts` — child role: redirect from /dashboard to own account page; block /child/:childId routes; only allow own-data routes
- [x] T059 [US6] Update existing frontend pages for child context — modify pages that show data (AccountsPage, TransactionsPage, WishlistPage, etc.) to omit child_id param when user is child (API auto-filters by JWT); hide ChildSelector component for child users; hide dashboard navigation for child users
- [x] T060 [US6] Add backend child-only enforcement in `backend/app/api/deps.py` — in resolve_child_id: if caller is child and child_id param differs from JWT user_id, raise 403; ensure child can never query another child's data even within same family

**Checkpoint**: Child view locked to own data. No sibling or dashboard access.

---

## Phase 10: User Story 7 — 多子女独立结算 (Priority: P2)

**Goal**: Monthly settlement runs per-child independently; one child's failure doesn't affect others

**Independent Test**: Family with 2 children with different balances → trigger settlement → verify independent results; simulate failure for one child → verify other still succeeds

**FRs**: FR-016, FR-017

### Implementation for User Story 7

- [x] T061 [US7] Modify settlement service in `backend/app/services/settlement.py` — change from single-user to per-family: get all children in family, loop over each child, for each child run settlement SOP in its own DB transaction with advisory lock `fambank_settlement_{user_id}`; collect per-child results (completed/failed); return array of results; one child's exception doesn't abort others
- [x] T062 [US7] Modify settlement schemas in `backend/app/schemas/settlement.py` — update response schema for per-child results: settlement_date, results[] with child_id, child_name, settlement_id, status, steps
- [x] T063 [US7] Modify settlement API route in `backend/app/api/settlement.py` — require parent role; call modified settlement service with family_id from TenantContext; return per-child results
- [x] T064 [US7] Modify SettlementPage in `frontend/src/pages/SettlementPage.vue` — display per-child settlement results; show each child's name, status (completed/failed), and settlement steps; handle partial failures gracefully

**Checkpoint**: Per-child independent settlement works. Failure isolation verified.

---

## Phase 11: User Story 9 — 现有业务功能适配多租户 (Priority: P2)

**Goal**: All 001-fambank-core business features work in multi-tenant context with child_id

**Independent Test**: Execute full business flow (wishlist, purchase, spend, violation, redemption, config, announcement) in multi-tenant setup → all work correctly per-child and per-family

**FRs**: FR-026, FR-027, FR-028, FR-029, FR-030

**Depends on**: US4 (child_id pattern), US8 (tenant filtering)

### Implementation for User Story 9

- [x] T065 [P] [US9] Modify violations API in `backend/app/api/violations.py` — add child_id parameter (parent: required in body, child: N/A parent-only); use resolve_child_id; pass user_id to service; update request/response schemas inline if needed (add child_id to request body schema)
- [x] T066 [P] [US9] Modify wishlist API in `backend/app/api/wishlist.py` — add child_id parameter (parent: required query/body, child: auto-self); use resolve_child_id; pass user_id to service; update request/response schemas inline if needed
- [x] T067 [P] [US9] Modify redemption API in `backend/app/api/redemption.py` — add child_id parameter; use resolve_child_id; pass user_id to service; update request/response schemas inline if needed
- [x] T068 [P] [US9] Modify transactions API in `backend/app/api/transactions.py` — add child_id query parameter; use resolve_child_id; pass user_id to service for filtering
- [x] T069 [P] [US9] Modify config API in `backend/app/api/config.py` — filter by family_id from TenantContext; parent-only for POST /config/announce
- [x] T070 [US9] Update frontend API service in `frontend/src/services/api.ts` — add child_id parameters to all business API calls (wishlist, purchase, spend, violation, redemption, transactions); update type definitions
- [x] T071 [P] [US9] Update frontend business pages for child_id — modify WishlistPage, PurchasePage, SpendingPage, ViolationsPage, RedemptionPage to use ChildSelector (parent) or auto-self (child); pass child_id in API calls
- [x] T072 [US9] Remove all remaining PIN-related code from frontend — remove PIN input components, PIN confirmation dialogs from pages other than SettingsPage (SettingsPage PIN removal handled in T040); replace with role-based permission checks

**Checkpoint**: All 001 features work in multi-tenant mode. PIN fully removed.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, test updates, and cross-cutting improvements

- [x] T073 Update test fixtures in `backend/tests/conftest.py` — add fixtures for creating families, parent/child users with JWT tokens, multi-child setups; remove PIN-based fixtures
- [x] T074 [P] Update unit tests in `backend/tests/unit/` — update all existing unit tests to use multi-tenant fixtures (family_id, user_id); add tests for auth service (send_code, verify_code, refresh), family service (create, invite, join), tenant context
- [x] T075 [P] Update integration tests in `backend/tests/integration/` — update all existing integration tests to use JWT auth + family context; add cross-family isolation tests; add per-child settlement tests
- [ ] T076 Validate quickstart flow per `specs/002-multi-tenant-platform/quickstart.md` — run full dev setup, verify: register → create family → invite child → join → record income → settlement → dashboard
- [x] T077 Run ruff check and fix any linting issues across all modified backend files
- [x] T078 Run frontend build (`npm run build`) and fix any TypeScript errors across all modified frontend files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models must exist for services/deps)
- **US1 (Phase 3)**: Depends on Phase 2 (auth service, SMS provider, JWT deps)
- **US2 (Phase 4)**: Depends on Phase 2 + US1 (need login to create family)
- **US3 (Phase 5)**: Depends on US2 (need family to invite)
- **US8 (Phase 6)**: Depends on Phase 1 (models must already have family_id/user_id columns) + Phase 2 (TenantContext must be ready); modifies all business services to accept user_id and filter by family_id
- **US4 (Phase 7)**: Depends on US3 + US8 (need children in family + service filtering)
- **US5 (Phase 8)**: Depends on US4 (need children with accounts for dashboard)
- **US6 (Phase 9)**: Depends on US4 (need child accounts + frontend routing)
- **US7 (Phase 10)**: Depends on US4 + US8 (need per-child accounts + service filtering)
- **US9 (Phase 11)**: Depends on US4 + US8 (need child_id pattern + tenant filtering)
- **Polish (Phase 12)**: Depends on all user stories complete

### User Story Dependencies (graph)

```
Phase 1 (Setup)
    │
    v
Phase 2 (Foundation)
    │
    ├──> US1 (Auth, Phase 3)
    │       │
    │       v
    │    US2 (Family, Phase 4)
    │       │
    │       v
    │    US3 (Invite/Join, Phase 5)
    │       │
    │       v
    ├──> US8 (Isolation, Phase 6) ──────────────┐
    │       │                                     │
    │       v                                     │
    │    US4 (Multi-child Income, Phase 7) <──────┘
    │       │
    │       ├──> US5 (Dashboard, Phase 8)
    │       ├──> US6 (Child View, Phase 9)
    │       ├──> US7 (Settlement, Phase 10)
    │       └──> US9 (Business Adapt, Phase 11)
    │
    v
Phase 12 (Polish)
```

### Within Each User Story

- Models/schemas before services
- Services before API routes
- Backend before frontend
- Core implementation before UI polish

### Parallel Opportunities

**Phase 1 (Setup)**: T002–T005 (new models) all [P]; T007–T015 (model modifications) all [P]
**Phase 6 (US8)**: T042–T048 (service modifications) all [P]
**Phase 11 (US9)**: T065–T069 (API modifications) all [P]; T071 (frontend pages) [P] with T070
**Phase 12 (Polish)**: T074 + T075 (unit + integration tests) [P]

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all new model creation tasks in parallel:
Task: "Create Family model in backend/app/models/family.py"
Task: "Create Invitation model in backend/app/models/invitation.py"
Task: "Create SmsCode model in backend/app/models/sms_code.py"
Task: "Create RefreshToken model in backend/app/models/refresh_token.py"

# Then launch all model modification tasks in parallel:
Task: "Modify Account model in backend/app/models/account.py"
Task: "Modify Config model in backend/app/models/config.py"
Task: "Modify Settlement model in backend/app/models/settlement.py"
Task: "Modify TransactionLog model in backend/app/models/transaction.py"
Task: "Modify Violation model in backend/app/models/violation.py"
Task: "Modify Debt model in backend/app/models/debt.py"
Task: "Modify Escrow model in backend/app/models/escrow.py"
Task: "Modify WishList model in backend/app/models/wishlist.py"
Task: "Modify RedemptionRequest model in backend/app/models/redemption_request.py"
```

---

## Implementation Strategy

### MVP First (P1 User Stories)

1. Complete Phase 1: Setup (models + migration)
2. Complete Phase 2: Foundational (auth rewrite + TenantContext + deps)
3. Complete Phase 3: US1 — Auth works (register/login via phone+SMS)
4. Complete Phase 4: US2 — Family creation works
5. Complete Phase 5: US3 — Invite/join works, children get accounts
6. Complete Phase 6: US8 — All services enforce tenant isolation
7. Complete Phase 7: US4 — Multi-child income works
8. **STOP and VALIDATE**: Core multi-tenant flow functional end-to-end
9. Deploy/demo if ready

### Incremental Delivery (P2 Stories)

10. Add US5 (Dashboard) → Parent aggregated view
11. Add US6 (Child View) → Child self-only restriction
12. Add US7 (Settlement) → Per-child settlement
13. Add US9 (Business Adapt) → All features multi-tenant
14. Complete Phase 12: Polish → Tests, lint, quickstart validation

### Suggested MVP Scope

**Phases 1–7** (T001–T053): Delivers full multi-tenant auth, family management, invite/join, data isolation, and multi-child income. This is a functional end-to-end system.

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 78 |
| Phase 1 (Setup) | 17 tasks |
| Phase 2 (Foundation) | 8 tasks |
| US1 (Auth) | 4 tasks |
| US2 (Family) | 5 tasks |
| US3 (Invite/Join) | 6 tasks |
| US8 (Isolation) | 8 tasks |
| US4 (Income) | 5 tasks |
| US5 (Dashboard) | 4 tasks |
| US6 (Child View) | 3 tasks |
| US7 (Settlement) | 4 tasks |
| US9 (Business Adapt) | 8 tasks |
| Phase 12 (Polish) | 6 tasks |
| Parallelizable tasks | 32 (marked [P]) |
| MVP scope (P1) | Phases 1–7 (53 tasks) |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All monetary values: BIGINT cents in DB, Decimal in Python, string in JSON
- All services MUST use TenantContext for family_id filtering (Constitution VIII)
