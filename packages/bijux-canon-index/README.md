# bijux-canon-index

`bijux-canon-index` owns contract-driven vector execution in `bijux-canon`.

It owns:
- vector execution semantics
- provenance-aware artifacts and replay-oriented comparison
- plugin-backed vector store, embedding, and runner integration
- package-local API behavior

It does not own ingest document preparation, runtime authority, or repository tooling.

Start here:
- local package docs: [docs/index.md](docs/index.md)
- package-local architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- package-local public API: [docs/PUBLIC_API.md](docs/PUBLIC_API.md)

Source layout:
- [src/bijux_canon_index](src/bijux_canon_index)
- [tests](tests)
- [plugins](plugins)
- [benchmarks](benchmarks)
