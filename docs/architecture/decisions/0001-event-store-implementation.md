# ADR 0001 — Event Store Implementation: Postgres + Redis Streams Instead of a Broker (v1)

**Status:** Accepted
**Date:** 2026-07-09

## Context

Velora's founding architectural principle is that "everything that happens is an event" — state changes are derived from an event log, not the reverse, and the same event stream feeds Memory, the Audit Log, Analytics, and Billing (see [DomainModel.md §2.14](../DomainModel.md#214-event) and the platform's event-driven design philosophy). The original conceptual architecture assumed a Kafka/Pulsar-class broker as "the nervous system" connecting every service.

The concrete v1 stack decision, however, is FastAPI, PostgreSQL, Redis, LangGraph, and Qdrant — deliberately, as a **modular monolith**, not a distributed system of independently deployed services. There is no message broker in this stack. Introducing Kafka or Pulsar at Sprint 0, before there is more than one deployable unit to decouple, would add substantial operational surface (cluster management, schema registry, consumer group tooling) in service of a problem — cross-service decoupling — that doesn't exist yet.

## Decision

Implement the Event Store as a Postgres `events` table (append-only, `INSERT`-only role — [Database.md §3.11](../Database.md#311-event-store)), written in the same database transaction as the state change that produces it (the **transactional outbox pattern**). A background **Outbox Relay** process polls unrelayed rows (`relayed_at IS NULL`) in occurrence order per organization and publishes each to a **Redis Stream** named after the event's `topic` ([EventCatalog.md §2](../EventCatalog.md#2-naming-convention)), using Redis Streams' consumer groups for at-least-once delivery to downstream consumers (Memory Indexing, Audit Log projection, Analytics, Billing) within the monolith and its background workers.

This satisfies the same contract a broker would provide — durable, per-tenant-ordered, replayable events, with retry and dead-letter handling ([EventCatalog.md §4](../EventCatalog.md#4-delivery)) — using infrastructure already in the stack.

## Alternatives Considered

- **Adopt Kafka/Pulsar now, per the original conceptual draft.** Rejected for v1: pays real operational cost (cluster ops, schema registry, partition/consumer-group tuning) for a decoupling benefit that only matters once there are multiple independently deployed services. Premature for a modular monolith.
- **In-process pub/sub only (no durable log).** Rejected: fails the "everything that happens is an event, replayable, source of truth" principle outright — an in-memory event bus loses everything on a crash and cannot be replayed to rebuild a projection, which is a hard requirement for the Memory/Audit Log/Analytics/Billing consumers all needing to derive consistent state from the same history.
- **Postgres `LISTEN`/`NOTIFY` instead of Redis Streams for relay.** Rejected: no consumer-group semantics, no persistence of undelivered notifications across a consumer restart, and payload size limits — Redis Streams gives durable, replayable, consumer-group delivery with materially less custom code.

## Consequences

- **Easier:** no new infrastructure to operate at Sprint 0; the event contract (envelope, catalog, delivery guarantees) is fully real and testable now, not deferred behind a "we'll add Kafka eventually" placeholder; migrating to a real broker later is a relay-implementation swap, not a rethink of the event model, since producers only ever write to the `events` table and never talk to Redis directly.
- **Harder:** Postgres write throughput on the `events` table is now a shared resource with the rest of the OLTP workload — needs the partitioning treatment described in [Database.md §4](../Database.md#4-indexing-strategy) once volume warrants it, sooner than it would if events lived on dedicated broker infrastructure from day one.
- **Deferred, explicitly:** adopting a real broker (Kafka, Pulsar, Azure Service Bus/Event Hubs) is revisited specifically when module extraction ([Deployment.md §8](../Deployment.md#8-scaling-path-deployment-dimension)) produces genuinely independent deployables that need decoupling across a network boundary — not on a fixed timeline, and not because broker adoption is itself a goal.
