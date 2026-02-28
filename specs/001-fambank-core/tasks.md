# Tasks: FamBank 家庭内部银行核心系统

**Input**: Design documents from `/specs/001-fambank-core/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md

**Tests**: Included — constitution principle VI (测试覆盖) mandates unit tests for all financial formulas and integration tests for settlement SOP.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization, tooling, and basic structure

- [x] T001 Create backend project with uv: `uv init backend` with pyproject.toml, add dependencies (fastapi, uvicorn, pydantic, sqlalchemy, aiomysql, passlib, python-jose)
- [x] T002 Create frontend project with Vite + Vue 3 + TypeScript: `npm create vite@latest frontend -- --template vue-ts`
- [x] T003 [P] Configure backend linting and formatting (ruff) in backend/pyproject.toml
- [x] T004 [P] Configure frontend linting (eslint) and formatting (prettier) in frontend/package.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement MySQL database connection and session management in backend/app/database.py (connection pool, transaction helper)
- [x] T006 Create database migration script with all tables from data-model.md in backend/app/migrations/init.sql (User, Account, Transaction, WishList, WishItem, Settlement, Violation, Config, Announcement, Debt, Escrow)
- [x] T007 Create MySQL trigger on Transaction table to prevent UPDATE and DELETE (audit immutability) in backend/app/migrations/triggers.sql
- [x] T008 [P] Implement Account model (A/B/C with balance, interest_pool, suspension states) in backend/app/models/account.py
- [x] T009 [P] Implement Transaction model (audit log entry with all fields from data-model) in backend/app/models/transaction.py
- [x] T010 [P] Implement User model (parent/child roles, PIN hash) in backend/app/models/user.py
- [x] T011 [P] Implement Config model (key-value with effective_from, announced_at) in backend/app/models/config.py
- [x] T012 Implement PIN/password auth service with bcrypt hashing and session tokens in backend/app/auth.py
- [x] T013 Implement FastAPI app entry point with CORS, router mount, static file serving in backend/app/main.py
- [x] T014 [P] Implement Pydantic base schemas for Money type (Decimal string ↔ integer cents conversion) in backend/app/schemas/common.py
- [x] T015 [P] Implement auth API endpoints (POST /auth/login) in backend/app/api/auth.py
- [x] T016 [P] Implement auth middleware (role-based access: parent vs child permissions) in backend/app/api/deps.py
- [x] T017 Seed default config values (split ratios, interest rates, penalty multiplier, etc.) in backend/app/migrations/seed.sql
- [x] T018 [P] Create frontend API client service (fetch wrapper with session token, Decimal string handling) in frontend/src/services/api.ts
- [x] T019 [P] Create Vue router with page routes (login, dashboard, income, wishlist, transactions, settlement) in frontend/src/router/index.ts
- [x] T020 [P] Implement LoginPage.vue (PIN input, role detection, session storage) in frontend/src/pages/LoginPage.vue
- [x] T021 Create backend test fixtures (test DB setup/teardown, seeded accounts, conftest) in backend/tests/conftest.py

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — 收入入账与自动分流 (Priority: P1) MVP

**Goal**: 乙方录入收入，系统按 15%/30%/55% 自动分流至 A/B/C 三账户

**Independent Test**: 录入一笔金额，验证三账户余额按比例正确变化

### Tests for User Story 1

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T022 [P] [US1] Unit test for income split calculation (100元, 0.01元 tail-diff, negative input rejection) in backend/tests/unit/test_income_split.py
- [x] T023 [P] [US1] Integration test for POST /income endpoint (full split flow, balance verification, audit records) in backend/tests/integration/test_income.py

### Implementation for User Story 1

- [x] T024 [US1] Implement income split service: calculate split amounts with Decimal, handle tail-diff (remainder to C), create 3 Transaction records, update 3 Account balances, handle B deposit-suspended escrow in backend/app/services/income.py
- [x] T025 [US1] Implement income API schemas (request: amount+description, response: splits+balances) in backend/app/schemas/income.py
- [x] T026 [US1] Implement POST /income endpoint with auth (child or parent) in backend/app/api/income.py
- [x] T027 [US1] Implement GET /accounts endpoint (return all 3 account balances + B details + debt) in backend/app/api/accounts.py
- [x] T028 [P] [US1] Implement DashboardPage.vue (3 account cards with balances, B shows principal + interest pool + P_active) in frontend/src/pages/DashboardPage.vue
- [x] T029 [P] [US1] Implement AccountCard.vue component (balance display, account type icon/color) in frontend/src/components/AccountCard.vue
- [x] T030 [US1] Implement IncomePage.vue (amount input form, submit, show split result) in frontend/src/pages/IncomePage.vue

**Checkpoint**: User Story 1 fully functional — income flows into 3 accounts correctly

---

## Phase 4: User Story 2 — 月度结算 (Priority: P1) MVP

**Goal**: 甲方触发月度结算，四步 SOP 原子执行（C派息→B溢出→B计息→违约划转）

**Independent Test**: 预设账户余额，执行结算，验证每步计算结果与章程公式一致

### Tests for User Story 2

- [x] T031 [P] [US2] Unit test for C dividend calculation (C_prin × 5% ÷ 12) in backend/tests/unit/test_interest_calc.py (C section)
- [x] T032 [P] [US2] Unit test for B tiered interest calculation (Tier1/2/3 boundaries, suspended=0) in backend/tests/unit/test_interest_calc.py (B section)
- [x] T033 [P] [US2] Unit test for B overflow calculation (Cap_overflow = 1.2 × P_active, boundary: equal = no overflow, greater = overflow) in backend/tests/unit/test_overflow.py
- [x] T034 [US2] Integration test for full settlement SOP (4 steps in order, atomic rollback on failure, concurrent lock) in backend/tests/integration/test_settlement_sop.py
- [x] T035 [P] [US2] Integration test for fund conservation (total_balances + total_spent + total_penalties == total_income) in backend/tests/integration/test_fund_conservation.py

### Implementation for User Story 2

- [x] T036 [US2] Implement interest calculation service: C dividend, B tiered interest (Tier1/2/3 with Decimal) in backend/app/services/interest.py
- [x] T037 [US2] Implement overflow service: Cap_overflow calculation, B→C transfer in backend/app/services/overflow.py
- [x] T038 [US2] Implement Settlement model in backend/app/models/settlement.py
- [x] T039 [US2] Implement settlement SOP service: acquire MySQL advisory lock (GET_LOCK) to block concurrent income/spending during settlement, atomic 4-step execution within single MySQL transaction (C dividend → B overflow → B interest → violation transfer), B interest suspension check (12-month timer from last compliant purchase or wish list registration, FR-012), snapshot before/after, duplicate month guard, release lock on completion in backend/app/services/settlement.py
- [x] T040 [US2] Implement settlement API schemas in backend/app/schemas/settlement.py
- [x] T041 [US2] Implement POST /settlement and GET /settlements endpoints (parent-only auth) in backend/app/api/settlement.py
- [x] T042 [P] [US2] Implement SettlementReport.vue component (step-by-step breakdown: dividend, overflow, interest, violation transfer) in frontend/src/components/SettlementReport.vue
- [x] T043 [US2] Implement SettlementPage.vue (trigger button, settlement history list, report detail) in frontend/src/pages/SettlementPage.vue

**Checkpoint**: MVP complete — income + settlement form a full monthly cycle

---

## Phase 5: User Story 3 — 愿望清单管理 (Priority: P2)

**Goal**: 乙方提交愿望清单，系统管理备案/锁定期/P_active

**Independent Test**: 提交清单、验证均价/最高价、锁定期拒绝、P_active 切换

### Tests for User Story 3

- [x] T044 [P] [US3] Unit test for wish list calculations (avg_price, max_price, p_active switching) in backend/tests/unit/test_wishlist.py
- [ ] T045 [P] [US3] Integration test for wish list CRUD (create, lock period rejection, price update limit, target declaration) in backend/tests/integration/test_wishlist.py

### Implementation for User Story 3

- [x] T046 [P] [US3] Implement WishList and WishItem models in backend/app/models/wishlist.py
- [x] T047 [US3] Implement wish list service: create/replace (lock check), price update (monthly limit), avg/max calc, declare target, validate p_active in backend/app/services/wishlist.py
- [x] T048 [US3] Implement wish list API schemas in backend/app/schemas/wishlist.py
- [x] T049 [US3] Implement wish list API endpoints (GET, POST, PATCH price, POST/DELETE declare-target) in backend/app/api/wishlist.py
- [x] T050 [US3] Implement WishListPage.vue (list display, add form with price+URL, lock countdown, declare target button, price update) in frontend/src/pages/WishListPage.vue

**Checkpoint**: Wish list active, P_active drives B account overflow and interest tiers

---

## Phase 6: User Story 4 — 账户B购买消费 (Priority: P2)

**Goal**: 乙方使用B账户购买清单标的，合规校验 + 先本金后利息池扣款

**Independent Test**: 预设B余额和清单，发起购买，验证合规校验和扣款顺序

### Tests for User Story 4

- [x] T051 [P] [US4] Unit test for purchase compliance (in-list check, 120% substitute limit, balance sufficiency, deduction order) in backend/tests/unit/test_purchase.py
- [ ] T052 [P] [US4] Integration test for B purchase flow (full deduction, substitute approval, interest resume on purchase) in backend/tests/integration/test_purchase.py

### Implementation for User Story 4

- [x] T053 [US4] Implement purchase service: compliance validation, deduction (principal first, then interest pool), substitute approval flow, B interest resume trigger in backend/app/services/purchase.py
- [x] T054 [US4] Implement purchase API schemas (request with wish_item_id + cost + substitute flag, response with deduction breakdown) in backend/app/schemas/purchase.py
- [x] T055 [US4] Implement POST /accounts/b/purchase and POST /accounts/b/purchase/approve endpoints in backend/app/api/accounts.py (add to existing)
- [x] T056 [US4] Add purchase UI to WishListPage.vue or DashboardPage.vue (buy button per wish item, cost input, substitute toggle, approval status) in frontend/src/pages/WishListPage.vue (extend)
- [x] T057 [US4] Implement refund service: return funds to B (split back to principal/interest pool per original deduction record), create refund Transaction records with clause §6.2 in backend/app/services/purchase.py (extend)
- [x] T058 [US4] Implement POST /accounts/b/refund endpoint and schemas in backend/app/api/accounts.py (extend) + backend/app/schemas/purchase.py (extend)

**Checkpoint**: B account purchase cycle complete (wish list → purchase → refund → resume interest)

---

## Phase 7: User Story 8 — 交易记录与审计查询 (Priority: P2)

**Goal**: 甲乙双方查看完整交易记录，支持按账户/时间/类型筛选

**Independent Test**: 执行若干操作后查询，验证记录完整性和筛选正确性

### Tests for User Story 8

- [ ] T059 [P] [US8] Integration test for transaction query (filter by account, type, date range, pagination, audit completeness) in backend/tests/integration/test_transactions.py
- [ ] T060 [P] [US8] Integration test for audit immutability (attempt UPDATE/DELETE on transaction table, verify rejection) in backend/tests/integration/test_audit_immutability.py

### Implementation for User Story 8

- [x] T061 [US8] Implement transaction query service (filter, paginate, format charter clause) in backend/app/services/transaction.py
- [x] T062 [US8] Implement transaction API schemas (query params, paginated response) in backend/app/schemas/transaction.py
- [x] T063 [US8] Implement GET /transactions endpoint in backend/app/api/transactions.py
- [x] T064 [P] [US8] Implement TransactionList.vue component (table with timestamp, type, account, amount, balance before/after, clause) in frontend/src/components/TransactionList.vue
- [x] T065 [US8] Implement TransactionsPage.vue (filter controls: account select, date range picker, type filter, paginated list) in frontend/src/pages/TransactionsPage.vue

**Checkpoint**: Full audit trail viewable and filterable

---

## Phase 8: User Story 5 — 账户A自由消费 (Priority: P3)

**Goal**: 乙方使用 A 账户自由消费，不透支

**Independent Test**: 预设A余额，消费成功/拒绝透支

### Tests for User Story 5

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T066 [P] [US5] Unit test for A spending (balance deduction, overdraft rejection, zero balance edge case) in backend/tests/unit/test_spending.py

### Implementation for User Story 5

- [x] T067 [US5] Implement A spending service (balance check, acquire advisory lock to prevent concurrent settlement, deduct, create transaction with clause §3) in backend/app/services/spending.py
- [x] T068 [US5] Implement POST /accounts/a/spend endpoint and schemas in backend/app/api/accounts.py (extend) + backend/app/schemas/spending.py
- [x] T069 [US5] Add quick-spend UI to DashboardPage.vue (A card → spend button → amount input → confirm) in frontend/src/pages/DashboardPage.vue (extend)

**Checkpoint**: A account spending functional

---

## Phase 9: User Story 6 — 违约处理 (Priority: P3)

**Goal**: 甲方录入违约，系统执行罚金计算和划转

**Independent Test**: 预设账户状态，录入违约，验证罚金和升级条款

### Tests for User Story 6

- [x] T070 [P] [US6] Unit test for penalty calculation (min(B_int_pool, 2W), edge: pool < 2W, pool = 0) in backend/tests/unit/test_penalty.py
- [ ] T071 [P] [US6] Integration test for violation flow (penalty transfer, A→C violation transfer in settlement, escalation on 2nd in 12mo) in backend/tests/integration/test_violation.py

### Implementation for User Story 6

- [x] T072 [P] [US6] Implement Violation and Debt models in backend/app/models/violation.py + backend/app/models/debt.py
- [x] T073 [US6] Implement violation service: penalty calc, B_int→C transfer, escalation check (2nd in 12mo → suspend deposit), debt creation when A insufficient in backend/app/services/violation.py
- [x] T074 [US6] Implement debt repayment logic: hook into income split to divert A portion to debt repayment in backend/app/services/income.py (extend)
- [x] T075 [US6] Implement POST /violations endpoint and schemas (parent-only) in backend/app/api/violations.py + backend/app/schemas/violation.py
- [x] T076 [US6] Integrate violation transfer into settlement SOP step 4 in backend/app/services/settlement.py (extend)
- [x] T077 [US6] Implement ViolationPage.vue (parent-only: violation entry form with amount + description, violation history list, debt status display) in frontend/src/pages/ViolationPage.vue

**Checkpoint**: Violation + penalty + debt + escalation fully operational

---

## Phase 10: User Story 7 — 账户C紧急赎回 (Priority: P3)

**Goal**: 双方确认后 C 账户紧急赎回，10%违约金

**Independent Test**: 预设C本金，赎回申请/确认，验证违约金和净额

### Tests for User Story 7

- [x] T078 [P] [US7] Unit test for redemption fee (10% fee, net = 90%, insufficient balance rejection) in backend/tests/unit/test_redemption_fee.py
- [ ] T079 [P] [US7] Integration test for redemption flow (request → pending → approve → C deduct → A credit) in backend/tests/integration/test_redemption.py

### Implementation for User Story 7

- [x] T080 [US7] Implement redemption service: request (validate C balance), approve (deduct C, calc 10% fee, credit A net), reject in backend/app/services/redemption.py
- [x] T081 [US7] Implement POST /accounts/c/redemption/request and POST /accounts/c/redemption/approve endpoints and schemas in backend/app/api/redemption.py + backend/app/schemas/redemption.py
- [x] T082 [US7] Add redemption UI to DashboardPage.vue (C card → redeem button → amount input → pending status; parent view → approve/reject panel) in frontend/src/pages/DashboardPage.vue (extend)

**Checkpoint**: C emergency redemption with approval workflow complete

---

## Phase 11: User Story 9 — 规则参数配置与公告 (Priority: P3)

**Goal**: 甲方调整参数，提前1周期公告，存量保护

**Independent Test**: 甲方修改参数，验证公告期约束和存量保护

### Tests for User Story 9

- [ ] T083 [P] [US9] Integration test for config change flow (announce, verify pending, verify effective after cycle, legacy protection for active wish lists) in backend/tests/integration/test_config.py

### Implementation for User Story 9

- [x] T084 [P] [US9] Implement Announcement model in backend/app/models/config.py (extend)
- [x] T085 [US9] Implement config service: announce change (effective next cycle), apply pending announcements during settlement, legacy protection for active wish lists in backend/app/services/config.py
- [x] T086 [US9] Implement GET /config and POST /config/announce endpoints (parent-only) in backend/app/api/config.py + backend/app/schemas/config.py
- [x] T087 [US9] Integrate config effective-date check into income split and settlement services (use effective config values) in backend/app/services/income.py + backend/app/services/settlement.py (extend)
- [x] T088 [US9] Implement ConfigPage.vue (parent-only: current parameters display, change form with announcement preview, announcement history, effective date indicator) in frontend/src/pages/ConfigPage.vue

**Checkpoint**: Parameter governance with announcement and legacy protection complete

---

## Phase 12: Escrow — B暂停入金暂存 (Cross-cutting)

**Purpose**: 实现 B 账户暂停入金期间的资金暂存和恢复补入

- [x] T089 [P] Implement Escrow model in backend/app/models/escrow.py
- [x] T090 Implement escrow service: buffer B portion during deposit suspension, release on resume (bulk insert to B principal) in backend/app/services/escrow.py
- [x] T091 Integrate escrow into income split (check B deposit_suspended, divert to escrow) and settlement (auto-release after suspend period) in backend/app/services/income.py + backend/app/services/settlement.py (extend)

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T092 [P] Add responsive CSS styling across all pages (mobile-friendly layout) in frontend/src/
- [x] T093 [P] Add loading states, error toast notifications, and empty states to all pages in frontend/src/
- [x] T094 Add advisory lock check to income and spending services: verify settlement is not in progress before accepting writes in backend/app/services/income.py + backend/app/services/spending.py (extend)
- [x] T095 Run full test suite, fix failures, verify fund conservation across all scenarios
- [x] T096 Run quickstart.md validation (fresh setup → seed → income → settlement → verify)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational
- **US2 (Phase 4)**: Depends on Foundational (uses accounts created by US1 tests but structurally independent)
- **US3 (Phase 5)**: Depends on Foundational
- **US4 (Phase 6)**: Depends on US3 (needs wish list for purchase validation)
- **US8 (Phase 7)**: Depends on Foundational (reads transactions created by any story)
- **US5 (Phase 8)**: Depends on Foundational
- **US6 (Phase 9)**: Depends on Foundational + partially US2 (violation transfer in settlement)
- **US7 (Phase 10)**: Depends on Foundational
- **US9 (Phase 11)**: Depends on Foundational + partially US1/US2 (config used in split/settlement)
- **Escrow (Phase 12)**: Depends on US1 + US6 (triggered by deposit suspension from violations)
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### Parallel Opportunities

After Foundational phase completes:
- **Parallel Group A**: US1 + US3 + US5 + US7 + US8 (all independent)
- **Parallel Group B**: US2 (can start with US1 but independent structurally)
- **Sequential**: US4 after US3, US6 after US2, US9 after US1+US2, Escrow after US6

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before API endpoints
- API endpoints before frontend pages
- Story complete before moving to next priority

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (income split)
4. Complete Phase 4: US2 (settlement)
5. **STOP and VALIDATE**: Income + Settlement cycle works end-to-end
6. Deploy MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (income) → First usable feature
3. US2 (settlement) → Full monthly cycle (MVP!)
4. US3 (wish list) + US4 (purchase) → B account fully functional
5. US8 (audit) → Transparency
6. US5 + US6 + US7 → Complete feature set
7. US9 + Escrow + Polish → Governance and edge cases

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All monetary values: BIGINT cents in MySQL, Decimal in Python, string in JSON
- Every service function MUST create Transaction records with charter_clause reference
- Settlement MUST run in a single MySQL transaction (BEGIN...COMMIT/ROLLBACK)
- Total tasks: 96
