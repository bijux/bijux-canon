# Scope

`bijux-canon-index` exists to execute vector workloads under explicit contracts,
with enough provenance and replay context to explain the result later.

## In scope

- vector execution across supported backends and plugins
- embedding and runner integration needed to perform that execution
- provenance-aware result shaping and replay-oriented comparison
- package-local boundary behavior for index execution

## Out of scope

- ingest-specific document preparation and normalization
- runtime-wide governance, persistence, and policy enforcement
- repository tooling, release support, and documentation infrastructure

## Rule of thumb

If the change answers "how did this vector result happen, under which backend
capabilities, and with which replay guarantees," it likely belongs here.
