# BOUNDARIES

`bijux-canon-index` owns vector execution, provenance, replay-facing artifact comparison, and backend/plugin integration.

It does own:
- vector store and embedding backend integration
- deterministic and non-deterministic execution behavior
- index-facing API and CLI boundaries

It does not own:
- ingest document preparation and lexical retrieval policy from `bijux-canon-ingest`
- runtime-wide execution authority from `bijux-canon-runtime`
- repository maintenance tooling from `bijux-canon-dev`
