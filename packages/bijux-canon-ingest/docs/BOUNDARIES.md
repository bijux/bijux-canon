# BOUNDARIES

`bijux-canon-ingest` owns document ingestion, chunking, retrieval assembly, and package-facing ingest/query boundaries.

It does own:
- deterministic document transforms and retrieval composition
- package CLI and HTTP ingestion/query boundaries
- ingest-local adapters and observability helpers

It does not own:
- vector execution semantics from `bijux-canon-index`
- runtime authority and replay storage from `bijux-canon-runtime`
- monorepo maintenance tooling from `bijux-canon-dev`
