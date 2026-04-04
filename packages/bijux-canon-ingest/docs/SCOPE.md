# Scope

`bijux-canon-ingest` exists to ingest documents in a deterministic way and to
assemble the retrieval-oriented outputs that naturally belong next to ingest.

## In scope

- document preparation, cleaning, and chunking
- ingest-local retrieval and indexing assembly
- package-local CLI and HTTP boundaries
- ingest-specific adapters and support modules

## Out of scope

- standalone vector execution engines
- runtime-wide replay or persistence governance
- monorepo tooling and release automation

## Rule of thumb

If the change is about making document-derived output stable, understandable,
and ready for downstream retrieval work, it likely belongs here.
