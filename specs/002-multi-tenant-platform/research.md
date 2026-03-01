# Research: FamBank 多家庭多租户产品化

**Date**: 2026-03-01
**Branch**: `002-multi-tenant-platform`

## Decision 1: Multi-Tenant Data Isolation Strategy

**Decision**: Shared database with `family_id` column on all business tables + `user_id` on per-child tables. Service-layer enforced filtering via dependency injection.

**Rationale**:
- FamBank is a single MySQL instance; separate databases per tenant would be massive over-engineering for MVP.
- Adding `family_id` FK to every business table is the simplest approach with SQLAlchemy.
- A `TenantContext` dependency injected into all services provides the family_id from JWT, ensuring queries are always filtered without relying on callers.

**Alternatives considered**:
- Separate database per family: Rejected — operational complexity far exceeds benefit at current scale.
- Row-level security (MySQL policies): Rejected — MySQL doesn't natively support RLS like PostgreSQL. Would require switching DB engine.
- Schema-per-tenant: Rejected — same operational overhead as separate databases.

## Decision 2: Authentication Mechanism (SMS → JWT)

**Decision**: Phone + SMS verification code → JWT access/refresh token pair. Use PyJWT (already in project). Dev mode uses fixed code `123456`.

**Rationale**:
- Existing project already uses PyJWT with HS256. Extending to include `family_id` and refresh tokens is minimal change.
- SMS provider (Tencent Cloud SMS) abstracted behind an interface; dev mode returns fixed code without network call.
- Refresh token stored in DB (not stateless) to support revocation on family change.

**Alternatives considered**:
- Session-based auth: Rejected — JWT is already in use, switching adds unnecessary churn.
- Stateless refresh tokens: Rejected — need to invalidate on family join (family_id changes), DB-stored refresh tokens are simpler.
- OAuth2/OIDC: Rejected — over-engineering for phone+SMS auth, no third-party identity provider needed.

## Decision 3: Database Migration Strategy

**Decision**: New migration file `002_multi_tenant.sql` that ALTERs existing tables to add `family_id`/`user_id` columns and adjusts unique constraints. No ORM auto-migration (Alembic), manual SQL scripts consistent with 001.

**Rationale**:
- 001 used manual SQL migration files (`init.sql`, `seed.sql`). Maintaining consistency reduces cognitive load.
- The migration must handle existing data: create a default family, assign existing users/accounts to it.
- New tables (`family`, `invitation`, `sms_code`, `refresh_token`) created in the same migration.

**Alternatives considered**:
- Alembic auto-migrations: Rejected — project doesn't use Alembic, introducing it adds a dependency for a one-time migration.
- Drop and recreate all tables: Rejected — would lose existing data (even if dev-only, it's bad practice).

## Decision 4: Per-Child Account Scoping

**Decision**: Add `user_id` FK (pointing to child user) on `account`, `wish_list`, `settlement`, `violation`, `debt`, `escrow`, `redemption_request`, `transaction_log` tables. `config` and `announcement` scoped to `family_id` only (shared across family).

**Rationale**:
- Each child has independent A/B/C accounts and independent settlement. `user_id` on these tables enables per-child isolation.
- Config/announcement are family-level (shared between all children in a family), so only `family_id` needed.
- `transaction_log` gets both `family_id` (for family-level audit) and `user_id` (for child-level filtering).

**Alternatives considered**:
- Single `owner_id` field: Rejected — ambiguous whether it means family or child.
- Separate child_id field: Rejected — `user_id` is clearer since child IS a user.

## Decision 5: Settlement Per-Child Isolation

**Decision**: Settlement loop iterates over all children in the family. Each child's settlement is wrapped in its own DB transaction. Success/failure is independent per child.

**Rationale**:
- Constitution Principle IV requires atomic settlement per SOP run. Per-child atomicity satisfies this — each child's 4-step SOP is atomic.
- If child A's settlement fails, child B's can still succeed. This matches FR-017.
- Advisory lock changes from global `fambank_settlement` to per-child `fambank_settlement_{user_id}`.

**Alternatives considered**:
- Single transaction for all children: Rejected — one child's failure would roll back everyone.
- No advisory lock: Rejected — concurrent income during settlement must still be prevented per-child.

## Decision 6: Frontend Routing for Multi-Tenant

**Decision**: Add new routes: `/onboarding` (no-family state), `/dashboard` (parent aggregated view), `/child/:childId/*` (child detail view). Child users keep existing single-child routes. Parent routes add child selector context.

**Rationale**:
- Minimal disruption to existing page components. Child's view is essentially the same as current single-child view.
- Parent's dashboard is a new page. Drilling into a child reuses existing components with a `childId` context parameter.
- Onboarding page is a simple two-button gate (create family / join family).

**Alternatives considered**:
- Complete frontend rewrite: Rejected — existing components are functional, only need context injection.
- Nested layouts with family sidebar: Rejected — over-engineering for MVP, cards/list on dashboard suffices.

## Decision 7: Invitation Code Format

**Decision**: 8-character alphanumeric code (uppercase letters + digits, excluding ambiguous chars like O/0/I/1). Generated via `secrets.token_hex(4)` converted to base32-like encoding.

**Rationale**:
- Short enough to share verbally or via messaging. Uppercase-only avoids case sensitivity issues.
- One-time use with 7-day expiry stored in `invitation` table.
- Collision probability negligible given small user base.

**Alternatives considered**:
- UUID: Rejected — too long to share verbally.
- Numeric-only code: Rejected — 8 digits has higher collision probability than alphanumeric.
- Link-based invite (URL): Could be added later, code is the MVP mechanism.
