# bijux-canon-index

`bijux-canon-index` is the vector execution package in `bijux-canon`. It does
more than "run a nearest-neighbor query." It executes a declared vector
operation against a concrete backend, records enough provenance to explain the
result later, and supports replay-oriented comparison when determinism matters.

If you need to understand vector-store adapters, embedding execution,
capability profiles, replay semantics, or provenance-aware result comparison,
start here. If you need document preparation, runtime governance, or repository
tooling, you are outside this package's boundary.

## What this package owns

- vector execution semantics and backend orchestration
- provenance-aware result artifacts and replay-oriented comparison
- plugin-backed vector store, embedding, and runner integration
- package-local HTTP behavior and related schemas

## What this package does not own

- document ingestion and normalization
- runtime-wide authority, persistence, or replay policy
- repository maintenance automation

## Source map

- [`src/bijux_canon_index/core`](src/bijux_canon_index/core) for stable primitives and errors
- [`src/bijux_canon_index/domain`](src/bijux_canon_index/domain) for execution and provenance semantics
- [`src/bijux_canon_index/application`](src/bijux_canon_index/application) for package workflows
- [`src/bijux_canon_index/infra`](src/bijux_canon_index/infra) for backends, adapters, and plugins
- [`src/bijux_canon_index/interfaces`](src/bijux_canon_index/interfaces) and [`src/bijux_canon_index/api`](src/bijux_canon_index/api) for boundaries
- [`plugins`](plugins) for plugin development support
- [`tests`](tests) for conformance and replay protection

## Read this next

- [Package guide](docs/index.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Public API](docs/PUBLIC_API.md)
- [Mental model](docs/spec/mental_model.md)
- [Failure semantics](docs/spec/failure_semantics.md)
