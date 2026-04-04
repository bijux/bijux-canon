---
title: bijux-canon
audience: mixed
type: index
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# bijux-canon

The repository handbook explains the shared boundary around the monorepo:
package layout, schema governance, documentation standards, validation, and
release expectations that apply above any single package.

<div class="bijux-callout"><strong>The monorepo is a coordination layer.</strong>
Product behavior lives in the publishable packages under `packages/`. Shared
repository rules live here only when they genuinely belong above package level.</div>

## Pages in This Section

- [Platform Overview](platform-overview.md)
- [Repository Scope](repository-scope.md)
- [Workspace Layout](workspace-layout.md)
- [Package Map](package-map.md)
- [API and Schema Governance](api-and-schema-governance.md)
- [Local Development](local-development.md)
- [Testing and Validation](testing-and-validation.md)
- [Release and Versioning](release-and-versioning.md)
- [Documentation System](documentation-system.md)

## Shared Package Map

- [bijux-canon-ingest](../bijux-canon-ingest/foundation/index.md) for deterministic document ingestion, chunking, retrieval assembly, and ingest-facing boundaries.
- [bijux-canon-index](../bijux-canon-index/foundation/index.md) for contract-driven vector execution with replay-aware determinism, audited backend behavior, and provenance-rich result handling.
- [bijux-canon-reason](../bijux-canon-reason/foundation/index.md) for deterministic evidence-aware reasoning, claim formation, verification, and traceable reasoning workflows.
- [bijux-canon-agent](../bijux-canon-agent/foundation/index.md) for deterministic, auditable agent orchestration with role-local behavior, pipeline control, and trace-backed results.
- `bijux-canon-runtime` for governed execution and replay authority with auditable non-determinism handling, persistence, and package-to-package coordination.

## Purpose

This page explains how to use the repository handbook without duplicating the package-specific detail that belongs in the package handbooks.

## Stability

This page is part of the canonical docs spine. Keep it aligned with the current repository layout and the actual package set declared in `pyproject.toml`.
