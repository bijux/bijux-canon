# bijux-canon-ingest

`bijux-canon-ingest` owns deterministic document ingestion and retrieval assembly in `bijux-canon`.

It owns:
- document preparation and chunking
- ingest-local retrieval and indexing assembly
- package-local CLI and HTTP boundaries
- ingest-specific adapters and observability helpers

It does not own standalone vector execution engines, runtime authority, or repository tooling.

Start here:
- local package docs: [docs/index.md](docs/index.md)
- package layout and ownership map: [docs/LAYOUT.md](docs/LAYOUT.md)
- package-local architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- package-local scope: [docs/SCOPE.md](docs/SCOPE.md)

Source layout:
- [src/bijux_canon_ingest](src/bijux_canon_ingest)
- [tests](tests)
