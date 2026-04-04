# Boundaries

`bijux-canon-index` is the place where vector execution becomes concrete.

## This package owns

- vector-store and embedding integration
- deterministic and non-deterministic execution behavior for index workloads
- provenance-aware result comparison and replay-facing bookkeeping
- package-local boundary behavior for index execution

## Neighbor packages own

- `bijux-canon-ingest`: document preparation and ingest-local retrieval assembly
- `bijux-canon-runtime`: execution authority, persistence, and replay governance
- `bijux-canon-dev`: repository tooling and maintenance automation

## Boundary discipline

- do not absorb ingest-specific content preparation here
- do not let runtime governance leak into backend adapters
- do not allow backend quirks to redefine stable package contracts silently
