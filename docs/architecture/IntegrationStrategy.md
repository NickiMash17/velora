# Integration Strategy

**Status:** v1.0 — Foundational
**Owner:** Platform Engineering / Integrations
**Depends on:** [Security.md §2, §6](./Security.md#2-identity-model), [API.md §9](./API.md#9-webhooks-outbound), [AIEmployees.md](./AIEmployees.md)

---

## 1. Purpose

Velora's Digital Employees are only as useful as the systems they can act in — email, Slack, Google Workspace, Microsoft 365, GitHub, Jira, WhatsApp, calendars. This document defines how Velora integrates with external systems: the shared architectural pattern every integration follows, the auth model, and provider-specific notes. The goal is that adding the *next* integration is implementing one interface, not writing a bespoke pipeline.

## 2. Core Principle: A Connector Framework, Not N Bespoke Integrations

Every external system integration implements the same **Connector** contract, conceptually:

```
Connector
  authenticate(org) -> Credential           # OAuth or API-key flow, provider-specific
  receive_webhook(raw_payload) -> Event[]    # normalize provider payload into internal Events
  execute_action(skill_call) -> Result        # outbound side effect (send email, post message, create ticket...)
  refresh_credential(credential) -> Credential
```

Concretely, a Connector is implemented as a Skill Runtime plugin: `execute_action` is what gets invoked when a Digital Employee calls a bound Skill whose implementation targets that provider ([AIEmployees.md §7](./AIEmployees.md#7-execution-model), [Database.md §3.3](./Database.md#33-ai-workforce)), and `receive_webhook` feeds the Webhook Gateway (§5). Every connector is registered in the Skill Catalog with its own declared `input_schema` and `required_permission_scope`, same as any other Skill — there is no separate "integration" code path that bypasses the Policy Engine.

**Why this matters for a ten-year platform:** the alternative — a growing pile of one-off integration modules, each with its own auth handling, retry logic, and event mapping — is exactly how integration code becomes unmaintainable at scale. A single well-designed interface, implemented N times, keeps the marginal cost of integration #12 close to the cost of integration #2.

## 3. OAuth as the Common Auth Backbone

Slack, Google Workspace, Microsoft 365, GitHub, Jira, and HubSpot-class integrations all authenticate via **OAuth2 authorization code flow**, initiated by an org admin from the Velora UI:

1. Org admin initiates connection → Velora redirects to the provider's OAuth consent screen with the **minimum required scope** for the skills the org intends to use (not a maximal "just in case" scope grab).
2. On consent, the provider redirects back with an authorization code; Velora exchanges it for access + refresh tokens.
3. Tokens are encrypted and stored in Azure Key Vault, associated with the connection (`origin_connector_id` — [Database.md §3.7](./Database.md#37-knowledge) for Knowledge Sources; skill execution follows the same credential lookup), never in application-layer storage or agent working memory ([Security.md §6](./Security.md#6-encryption)).
4. The **Token Refresh Service** proactively refreshes tokens before expiry; on refresh failure (revoked access, expired refresh token) it emits `IntegrationTokenRefreshFailed` ([EventCatalog.md §5.9](./EventCatalog.md#59-integration)) so the org admin is notified rather than a Digital Employee silently failing mid-task.
5. At execution time, the Skill Runtime requests a **short-lived lease** on the credential from the vault — it is never cached beyond the single skill call's execution window.

Integrations without a standard OAuth surface (e.g., WhatsApp Business API, some email providers) use provider-specific API-key or business-account authentication, but the storage, leasing, and rotation discipline above applies identically.

## 4. Provider Notes

| Provider | Inbound | Outbound | Notes |
|---|---|---|---|
| **Email** | Inbound parsing via a routing address per org/department (e.g., `support@{org}.velora.ai` or a connected mailbox) | Transactional send via a dedicated provider (not a shared IP pool with unrelated tenants for deliverability reasons) | Highest-volume, highest-trust-required integration — inbound content is a primary prompt-injection surface, always passed through the Guardrail Service ([Security.md §8.1](./Security.md#81-prompt-injection)) before reaching any Digital Employee |
| **Slack** | Events API (message posted, mention) via a per-workspace OAuth app | Web API (post message, update message) | Workspace-level OAuth, not per-user — a Digital Employee posts as itself (a distinct Slack bot identity), not impersonating a human |
| **Google Workspace** | Gmail/Drive/Calendar push notifications (webhook-based, provider requires a renewal cadence) | Gmail API, Calendar API, Drive API | Scopes requested per capability the org actually enables — not one broad Workspace grant |
| **Microsoft 365** | Microsoft Graph webhooks | Graph API (mail, calendar, Teams) | Same scoping discipline as Google Workspace; Graph's unified API surface makes this the natural single connector for Outlook/Teams/OneDrive rather than three separate ones |
| **GitHub** | GitHub App installation webhooks (issue/PR events) | GitHub App installation token (repo-scoped, not a personal access token) | App-based, not OAuth-user-based — keeps the credential tied to the org's installation, survives individual human offboarding |
| **Jira** | Webhooks (issue created/updated) | REST API | Atlassian Connect / OAuth 2.0 (3LO), project-scoped where the org's Jira permissions allow |
| **WhatsApp** | WhatsApp Business Platform webhooks | Business API send (template-message constraints apply for the first outbound message in a 24h window) | Meta's template-approval and messaging-window rules are a hard external constraint the Skill Runtime must respect, not something Velora can architect around |
| **Calendar** | Unified across Google Calendar / Microsoft Calendar | Same | Abstracted behind one internal "Calendar" skill interface so a Digital Employee's scheduling logic doesn't need to know which provider a given org uses |

## 5. Webhooks

### 5.1 Inbound

The **Webhook Gateway** is the single entry point for all inbound provider webhooks (distinct from the client-facing API Gateway). It:

- Verifies the provider's signature (HMAC or provider-specific scheme) before processing anything — an unverified webhook is discarded, not queued.
- Normalizes the provider-specific payload into one or more internal Events (`IntegrationEventReceived` at minimum — [EventCatalog.md §5.9](./EventCatalog.md#59-integration)), attaching `organization_id` resolved from the webhook's registered connection, never from payload content.
- Is idempotent per provider delivery ID — providers retry webhook delivery on non-2xx or timeout; a duplicate delivery must not produce a duplicate internal Event.

### 5.2 Outbound

Covered in [API.md §9](./API.md#9-webhooks-outbound) — partner/integration consumers subscribing to Velora's own event stream. Not duplicated here.

## 6. Future MCP Support

The **Model Context Protocol (MCP)** is explicitly deferred for v1 (consistent with the platform-wide non-goal on cross-org/external agent marketplaces) but the Connector Framework (§2) is deliberately shaped to support it later in both directions without a redesign:

- **Velora as an MCP server:** the Skill Catalog could be exposed as MCP tools, letting an external MCP-compatible client invoke Velora Skills — subject to exactly the same Policy Engine checks, permission scoping, and audit logging as any internally-triggered skill call. No special trust path for MCP-originated calls.
- **Velora as an MCP client:** the Skill Runtime could treat an external MCP server as an additional tool source for a Digital Employee, alongside its native Skills — subject to the same Guardrail/sandboxing requirements as any other skill ([Security.md §8](./Security.md#8-ai-specific-threat-model)). An MCP-provided tool is not a shortcut around permission scoping or spend caps.

This is a direction, not a commitment — it is recorded here so that when it becomes a real priority, the Connector interface doesn't need to be reshaped to accommodate it.

## 7. Non-Goals (v1)

- No generic "build your own integration" low-code framework for end users — integrations are built and maintained by Velora engineering against the Connector contract, not user-authored.
- No support for arbitrary/unlisted providers via generic HTTP+OAuth config — each provider in §4 is a deliberate, reviewed integration, not a configuration-driven free-for-all (which tends to produce untestable, unmaintainable edge cases).
- No MCP support shipped in v1 — §6 describes design intent, not a current capability.
