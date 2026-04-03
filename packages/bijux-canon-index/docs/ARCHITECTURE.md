# ARCHITECTURE

`bijux-canon-index` is a contract-driven vector execution package.

Core layout:
- `src/bijux_canon_index/core/` owns stable execution types, errors, and primitives
- `src/bijux_canon_index/domain/` owns execution, provenance, and drift semantics
- `src/bijux_canon_index/application/` owns orchestration and package-facing facades
- `src/bijux_canon_index/infra/` owns vector stores, embeddings, runners, and plugin loading
- `src/bijux_canon_index/interfaces/` and `api/v1/` own CLI and HTTP boundaries
- `src/bijux_canon_index/tooling/` owns benchmark support

The architecture should keep vector execution semantics in the core/domain layers and adapters at the edges.
