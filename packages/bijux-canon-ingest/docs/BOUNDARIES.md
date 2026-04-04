# Boundaries

`bijux-canon-ingest` is responsible for preparing content, not for governing the
entire system that uses that content later.

## This package owns

- deterministic document transforms and chunking
- ingest-local retrieval composition
- package-local ingestion and query boundaries
- ingest-specific adapters and observability helpers

## Neighbor packages own

- `bijux-canon-index`: vector execution semantics
- `bijux-canon-runtime`: runtime authority, replay, and storage governance
- `bijux-canon-dev`: repository maintenance tooling

## Boundary discipline

- do not move vector-engine concerns into ingest convenience helpers
- do not let runtime authority leak into package-local workflows
- do not let generic repository automation settle inside ingest modules
