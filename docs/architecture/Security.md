# Security

**Status:** v1.0 — Foundational
**Owner:** Platform Engineering / Security
**Depends on:** [Database.md](./Database.md), [AIEmployees.md](./AIEmployees.md), [CompanyDNA.md](./CompanyDNA.md), [Memory.md](./Memory.md)

---

## 1. Purpose

This document defines authentication, authorization, tenant isolation, encryption, and the AI-specific threat model for Velora. It is the one document in this folder that other documents defer to rather than override — if another doc appears to describe a permission model that conflicts with this one, this document wins until both are reconciled.

## 2. Identity Model

Three distinct identity types exist; they are never interchangeable and never share credential material:

| Identity type | AuthN mechanism | Notes |
|---|---|---|
| **Human user** | Password + MFA, OAuth (Google/Microsoft), or enterprise SSO (SAML/OIDC) with SCIM for provisioning/deprovisioning | May belong to multiple organizations (§3.2) |
| **Digital Employee** | Scoped machine identity — short-lived signed token, auto-rotated | Never a copy of a human's credential; see [AIEmployees.md §5](./AIEmployees.md#5-identity--machine-credentials) |
| **External integration** | OAuth2 token per connected account, encrypted at rest, minimum required scope | Refreshed by a dedicated Token Refresh Service, never cached in agent working memory |

Every action in the system must be attributable to exactly one identity of one of these types. There is no shared "system" account that actions can be attributed to as a fallback.

## 3. Session & Token Model

### 3.1 AuthN Flow

1. User or Digital Employee authenticates → Auth Service issues a short-lived access token (JWT, ~15 min) + rotating refresh token (stored hashed, never in plaintext).
2. Access token claims: `sub` (user or ai_employee id), `organization_id`, `role`, `token_version` (enables fast revocation without a DB lookup on the hot path). `role` is singular, not plural: a token scopes to exactly one organization (§3.2), and `organization_memberships` has a `UNIQUE(organization_id, user_id)` constraint — there is exactly one role per organization per user, never more than one to enumerate.
3. The API Gateway validates signature + expiry locally (no round-trip per request); a background revocation-list sync via the Event Bus propagates compromised-token kill-switches within seconds, not on the next token refresh cycle.

**Milestone 3/4 note:** a freshly-registered user belongs to no organization yet (organization creation is a separate concern — see [DomainModel.md](./DomainModel.md)). Login's access token therefore carries only `sub`, `token_version`, `iat`, `exp` — `organization_id`/`role` are simply absent, not null placeholders, and **login itself never changes this**: Milestone 4's organization creation and organization-selection flows are the only things that issue a fuller, scoped token, exactly as this section originally anticipated ("a future milestone's org-creation/switching flow is what first populates those claims"). See §3.1.2 for how that scoping survives a refresh, and §3.2 for the selection ("switching") flow itself.

HS256 (symmetric), not RS256, for now: the issuer and validator are the same process while there is no separate Gateway service ([Deployment.md §4](./Deployment.md#4-containerization--topology-v1)). RS256 becomes necessary once a Gateway needs to verify tokens without holding the signing secret — revisit at that point, not before.

### 3.1.1 Password Storage

Not specified elsewhere in this document until Milestone 3: passwords are hashed with **Argon2id** (`argon2-cffi`), OWASP's current default recommendation and the successor to bcrypt (memory-hard, resistant to GPU/ASIC-accelerated cracking). Password policy is minimum length only (8 characters) — per NIST 800-63B, composition rules (forced symbols/digits) are deliberately not used, since they push users toward predictable patterns without meaningfully raising entropy. Breach-list checking (e.g. an HaveIBeenPwned range-query lookup) is a valuable future addition, not a v1 requirement — it's a new external network dependency, out of proportion with Milestone 3's scope.

### 3.1.2 Refresh Token Lifecycle (v1 Implementation)

Not specified precisely enough elsewhere to implement blind — this is the concrete lifecycle Milestone 3 built, and future milestones should treat it as documented behavior, not re-derive it:

- **Storage:** an opaque, high-entropy secret (`secrets.token_urlsafe(32)`), never a JWT — nothing needs to inspect a refresh token's contents, it's purely a lookup key. Stored as a SHA-256 hash (not Argon2id — a generated high-entropy secret needs protection from database-dump exposure, not resistance to offline brute-force of a low-entropy human-chosen value, so a fast cryptographic hash is the correct, sufficient tool).
- **Rotation:** every successful refresh issues a new refresh token and immediately revokes the one presented (`revoked_at` set, `replaced_by_id` linked) — refresh tokens are single-use.
- **Family tracking:** every token descended from one login shares a `family_id`. Rotation preserves the family; it is never reset.
- **Replay protection:** presenting a token that has already been rotated (`revoked_at` is set) revokes the **entire family**, not just that one token — reuse of a dead token is the signal a refresh token has been stolen, and the correct response is to kill every token descended from the same login, forcing full re-authentication.
- **Expiry:** 30 days from issuance (configurable — `Settings.refresh_token_ttl_days`), sliding in the sense that each rotation gets a fresh 30-day window, not counted from the original login.
- **Organization scope carries across rotation (Milestone 4):** `refresh_tokens` carries its own nullable `organization_id`/`role`, mirroring whatever its access token's claims were. An ordinary refresh (`POST /v1/auth/refresh`, no override) **preserves** the rotated token's existing scope — an org-scoped session refreshing must not silently downgrade to org-less, which would otherwise happen roughly every 15 minutes (the access-token TTL) as a matter of course. Organization creation and organization selection (§3.2) both work by rotating the caller's *current* refresh token with an explicit `organization_id`/`role` **override**, inside the same family, rather than minting a second, independent, never-revoked family — "switching organizations issues an entirely new scoped token" (§3.2) is implemented as a rotation, not a parallel session.

### 3.2 Multi-Org Scoping

A human user may belong to multiple organizations (e.g., an agency managing client orgs — [Database.md §3.1](./Database.md#31-identity--organization)). A session token is scoped to **exactly one active organization at a time**. Switching organizations issues an entirely new scoped token rather than expanding the claims of the existing one — this is what makes cross-tenant data bleed via a stale or reused token structurally impossible, not just policy-discouraged.

**Milestone 4 implementation:** two endpoints perform this scoping, both returning `{organization, tokens}` so the client never needs an extra round trip before using the new session:

- `POST /v1/organizations` — creates a new organization, makes the caller its `org_admin`, and scopes the session to it in one step (session-creation, in this platform, always happens alongside organization-creation for the founding admin — there is no separate "create an org without entering it" state).
- `POST /v1/organizations/{organization_id}/select` — scopes the session to an organization the caller is *already* an active member of. This is the flow a returning user goes through: login (§3.1) always issues an org-less token regardless of prior organization membership, so a user with one or more existing organizations explicitly selects into one immediately afterward. Discovering which organization(s) a user belongs to before any tenant context exists is answered by `GET /v1/organizations`, backed by a dedicated self-visibility RLS policy — see [ADR 0002](./decisions/0002-organization-membership-self-visibility.md) for why that required a new, narrowly-scoped exception to the tenant-isolation policy rather than an application-level workaround.

Both endpoints require the caller's *current* refresh token in the request body (like `/v1/auth/refresh` already does) — organization scoping is a rotation of the existing session, not a bearer-token-only action.

### 3.3 Tenant Context Propagation

Tenant identification happens **once**, at the Gateway, derived from subdomain, custom domain, or API key — never re-derived downstream from user-supplied request fields. The Gateway attaches a signed, short-lived, internal-only **Tenant Context Token** (`organization_id`, `plan_tier`, `region`, `entitlements`) to every downstream call. Internal services trust this token; they do not re-authenticate the tenant themselves. This avoids N different services each having their own (possibly inconsistent) tenant-resolution logic.

## 4. Tenant Isolation

Tenant isolation is enforced redundantly at three layers — see [Database.md §2.2](./Database.md#22-enforcement-not-convention) for the full mechanics:

1. **Application layer** — no tenant-scoped repository method accepts an unscoped query.
2. **Database layer** — PostgreSQL Row-Level Security on every tenant-scoped table, keyed on a session-local `organization_id`, so a bug upstream still cannot leak rows.
3. **CI layer** — static lint checks flag unscoped queries on tenant-scoped tables; a cross-tenant-isolation test suite runs on every PR touching the data layer.

The same discipline extends to non-relational stores: Qdrant collections are namespaced per organization ([Memory.md §7](./Memory.md#7-data-model-notes), [CompanyDNA.md §5](./CompanyDNA.md#5-data-model)), and Redis keys are always prefixed with `organization_id`. There is no shared cache key space where a missing prefix could accidentally serve tenant A's cached value to tenant B.

**Escape hatch for regulated tenants:** enterprise/regulated organizations can be promoted to a dedicated schema or database instance (`isolation_tier = silo`), using identical application code — the isolation model changes at the infrastructure boundary, not by forking the codebase.

## 5. Authorization Model

Two authorization mechanisms, applied at different granularities:

- **RBAC** for coarse, human-facing permissions: `org_admin`, `department_manager`, `member`, `viewer` ([Database.md §3.1](./Database.md#31-identity--organization)).
- **ABAC / policy-based** for fine-grained Digital Employee permissions — e.g., "this Digital Employee may read CRM contacts in Department=Sales but may not send external email above a $-value threshold without human approval."

Both are enforced by a **centralized Policy Engine** (OPA-style, policy-as-code), queried by both human-facing services and the Agent Collaboration Layer **before any skill execution** — not reimplemented ad hoc inside each service. This centralization is what makes autonomy levels ([AIEmployees.md §6](./AIEmployees.md#6-human-oversight-model-autonomy-levels)) adjustable org-wide via policy change rather than requiring a code change per Digital Employee.

### 5.1 Delegated Authority

When a Digital Employee acts "on behalf of" a human (e.g., sending an email as a sales rep), the token chain preserves **both** identities — `acting_as` (the Digital Employee) and `on_behalf_of` (the human) — so that:

- Audit trails show both who the AI was and who authorized the action's context.
- The human's own downstream authorization limits still apply — a Digital Employee can never carry more authority than the human/policy that invoked it. This is enforced by the Policy Engine on **every** skill call, not just checked once at task assignment, closing the gap where a Digital Employee's authority could silently escalate mid-task.

### 5.2 Human-in-the-Loop Gates

Policy-flagged action categories (financial transactions, external communications above a risk threshold) require a signed human approval event before the Skill Runtime will execute them — this is the `approve` autonomy level from [AIEmployees.md §6](./AIEmployees.md#6-human-oversight-model-autonomy-levels), enforced structurally rather than as a UI convention.

**Data model decision (M5 Domain Contract review):** there is no dedicated Approval table. The gated action attaches to the Task it's blocking — a narrow `task_pending_approvals` record, 1:1 with `tasks` (`task_id` as both PK and FK), rather than a standalone polymorphic Approval domain. This is the smallest model consistent with the autonomy model above: the trigger is always a specific task's gated action, and the record exists only while that task is blocked awaiting sign-off. See [EventCatalog.md §5.6](./EventCatalog.md#56-goals-projects--tasks) for the three events this produces (`ApprovalRequested`/`Granted`/`Denied`, 📋 Planned). Documentation only as of this note — no table, migration, repository, or endpoint exists yet.

## 6. Encryption

| Layer | Mechanism |
|---|---|
| At rest | Per-tenant envelope encryption keys via Azure Key Vault; enterprise tenants may bring their own key (BYOK) |
| In transit | TLS 1.3 everywhere, including internal service-to-service traffic (mTLS via service mesh once the modular monolith begins splitting out services — see [Deployment.md](./Deployment.md)) |
| Secrets | All third-party integration credentials (OAuth tokens, API keys) live in Azure Key Vault, encrypted per tenant, accessed by the Skill Runtime only via short-lived leases at execution time — never cached in agent working memory ([Memory.md §7](./Memory.md#7-data-model-notes)) |

## 7. Audit Logging

The **Audit Log is immutable and append-only** — the database role used to write audit entries has `INSERT` only, no `UPDATE`/`DELETE` grant ([Database.md §3.6](./Database.md#36-audit--metering-relational-projections)). Entries are derived from the Event Bus, not independently written by each service, so the audit trail cannot drift from what actually happened at the event level. Target posture: cryptographically chained entries (each entry's hash includes the previous entry's hash) so tampering with historical entries is detectable, in line with SOC 2 Type II control expectations (§9).

## 8. AI-Specific Threat Model

Velora explicitly designs against four AI-native threats that a traditional SaaS threat model does not cover:

### 8.1 Prompt Injection

Malicious content in ingested documents, emails, or any retrieved external content attempting to hijack a Digital Employee's behavior. Mitigations:

- A **Guardrail Service** performs content classification on all retrieved Memory, DNA knowledge-layer, and external content **before** it reaches the Model Gateway.
- **Structural separation in prompt construction**: "instructions" (from DNA/system) and "data" (from retrieved memory/content) are marked distinctly in the prompt, so a model is not implicitly told to treat retrieved customer email content as an instruction to follow — see [CompanyDNA.md §6](./CompanyDNA.md#6-retrieval-at-invocation-time).

### 8.2 Privilege Escalation via Delegation

An AI Employee can never act with more authority than the human/policy that invoked it (§5.1) — enforced by the Policy Engine on every skill call, not only at task assignment, which is precisely the gap an escalation attempt would try to exploit (get broad authority once, then act beyond it repeatedly).

### 8.3 Cross-Tenant Data Leakage

Enforced structurally, not by convention: namespace isolation in Memory/Qdrant, `organization_id` scoping at the DB and cache layer, and CI-level lint rules banning unscoped queries (§4). Validated continuously via an automated cross-tenant-isolation test suite, not just at initial build time.

### 8.4 Runaway Agent Loops / Cost Bombs

Hard per-invocation and per-Department token/spend ceilings enforced at the **Model Gateway**, independent of any individual Digital Employee's own reasoning — a misbehaving planning loop cannot spend its way past a ceiling enforced outside its own control flow. Department budget caps ([Database.md §3.2](./Database.md#32-departments)) are the business-facing version of this same control.

## 9. Compliance Posture

- **SOC 2 Type II** control mapping is baked into the Audit Log Service design (§7) from the start, not bolted on later.
- **GDPR/CCPA** support via the Memory Governance redaction pipeline ([Memory.md §6.2](./Memory.md#62-right-to-forget)) and configurable data residency ([Database.md §2](./Database.md#2-multi-tenancy-model), region pinning on `organizations.region`).
- Enterprise tenants can be promoted to dedicated infrastructure for stricter isolation, BYOK encryption, and custom data residency guarantees (§4, §6) without a codebase fork.

## 10. Rate Limiting & Abuse Prevention

- Token-bucket limits per organization, per API key, and **per Digital Employee** — the per-employee limit exists specifically so a single runaway agent loop cannot starve the tenant's other Digital Employees, or (at the cell/infra level) other tenants.
- Input validation at every service boundary — request schema validation at the Gateway, and skill-input validation against each skill's declared JSON Schema before execution ([Database.md §3.3](./Database.md#33-ai-workforce), `skills.input_schema`).

### 10.1 Login Rate Limiting

A distinct problem from the above — brute-force login protection, not AI-runtime resource abuse — and one this document didn't specify until Milestone 3 built it. A Redis **fixed window** counter (`INCR` + `EXPIRE`, not a token bucket — simple, no Lua scripting, and correct enough for "block after N attempts in M seconds"), keyed on the **normalized email only**, deliberately with no organization/tenant dimension: login happens before any tenant context exists, so keying this on anything org-related would be a real mistake, not just an unnecessary one.

The counter increments **before** the credential check, unconditionally — this is what keeps rate-limit behavior identical whether or not the given email corresponds to a real account, satisfying "never reveal whether an email exists" the same way the login response itself does. Default: 5 attempts per 60-second window (`Settings.login_rate_limit_max_attempts`/`login_rate_limit_window_seconds`), returning `429` with `retry_after_seconds` in the error envelope's `details`.

## 11. Non-Goals (v1)

- No fully autonomous cross-org agent interaction — consistent with the platform-wide non-goal; there is no cross-tenant authorization model to design because the capability does not exist.
- No client-managed encryption key rotation UI in v1 — BYOK exists for enterprise tenants at the infrastructure/Key Vault level; a self-service rotation UI is a later product decision, not a v1 security requirement.
- No formal penetration-test/bug-bounty program commitment in this document — that is a security-operations decision to be made explicitly when the product has customer data in production, not implied by this architecture doc.
