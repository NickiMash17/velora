# Velora Documentation

This is the single source of truth for Velora's product, architecture, and engineering decisions. If it isn't written down here, it isn't official.

## Structure

| Folder | Purpose | Audience |
|---|---|---|
| [`company/`](./company/README.md) | Mission, vision, values, org structure | Everyone |
| [`architecture/`](./architecture/README.md) | System design, data models, security, deployment | Engineering |
| [`engineering/`](./engineering/README.md) | Coding standards, dev environment, contribution workflow | Engineering |
| [`product/`](./product/README.md) | Product specs, roadmaps, feature definitions | Product, Engineering, Design |
| [`design/`](./design/README.md) | Design system, UX guidelines, brand assets | Design, Frontend Engineering |
| [`pitch/`](./pitch/README.md) | Investor/external-facing materials | Founders, Leadership |

## Conventions

- **Format:** Markdown (`.md`), one topic per file. Prefer several focused documents over one sprawling one.
- **Ownership:** Every document should have an implicit or stated owner (a role, not necessarily a name) — see each doc's header.
- **Status:** Documents that are still placeholders are marked `Status: Placeholder`. Do not treat placeholder content as decided.
- **Versioning:** Architecture documents that describe systems still in flux should carry a `Status` and version note at the top (e.g., `v1.0 — Foundational`). Breaking changes to a system's design should bump the doc, not silently rewrite history — prefer amending with a changelog note over deleting prior rationale.
- **Cross-linking:** Reference other docs with relative Markdown links rather than repeating content. If you find yourself copy-pasting a table from another doc, link to it instead.

## Current Status

Sprint 0 — Foundation. Engineering documentation is being established before feature implementation begins. See [`architecture/README.md`](./architecture/README.md) for the current set of system design documents.
