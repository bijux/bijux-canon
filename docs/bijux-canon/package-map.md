---
title: Package Map
audience: mixed
type: guide
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-04-04
---

# Package Map

The canonical packages each own a distinct slice of the overall system:

- [bijux-canon-ingest](../bijux-canon-ingest/foundation/index.md) for deterministic document ingestion, chunking, retrieval assembly, and ingest-facing boundaries.
- [bijux-canon-index](../bijux-canon-index/foundation/index.md) for contract-driven vector execution with replay-aware determinism, audited backend behavior, and provenance-rich result handling.
- [bijux-canon-reason](../bijux-canon-reason/foundation/index.md) for deterministic evidence-aware reasoning, claim formation, verification, and traceable reasoning workflows.
- [bijux-canon-agent](../bijux-canon-agent/foundation/index.md) for deterministic, auditable agent orchestration with role-local behavior, pipeline control, and trace-backed results.
- `bijux-canon-runtime` for governed execution and replay authority with auditable non-determinism handling, persistence, and package-to-package coordination.

## Shared Maintainer Packages

- [bijux-canon-dev](../bijux-canon-dev/index.md) for repository automation, schema drift checks, SBOM support, and quality gates
- [compatibility packages](../compat-packages/index.md) for legacy distribution and import preservation

## Purpose

This page keeps the package relationships visible from one place before a reader dives into package-local detail.

## Stability

Update this page only when package ownership changes, not for ordinary internal refactors.
