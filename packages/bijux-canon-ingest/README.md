# bijux-canon-ingest

`bijux-canon-ingest` is the package that turns raw documents into deterministic
ingest artifacts and retrieval-ready structures. It is where cleaning,
chunking, package-local retrieval assembly, and ingest-facing boundaries live.

This package should help a maintainer answer practical questions such as:

- how does a source document become stable ingest output
- where do retrieval-oriented assembly steps belong
- which code is pure transformation logic and which code is adapter work

## What this package owns

- document cleaning, normalization, and chunking
- ingest-local retrieval and indexing assembly
- package-local CLI and HTTP boundaries
- ingest-specific adapters, safeguards, and observability helpers

## What this package does not own

- standalone vector execution semantics
- runtime-wide governance, persistence, or replay authority
- repository tooling and release automation

## Source map

- [`src/bijux_canon_ingest/processing`](src/bijux_canon_ingest/processing) for deterministic document transforms
- [`src/bijux_canon_ingest/retrieval`](src/bijux_canon_ingest/retrieval) for retrieval-oriented models and assembly
- [`src/bijux_canon_ingest/application`](src/bijux_canon_ingest/application) for package workflows
- [`src/bijux_canon_ingest/infra`](src/bijux_canon_ingest/infra) and [`src/bijux_canon_ingest/integrations`](src/bijux_canon_ingest/integrations) for adapters
- [`src/bijux_canon_ingest/interfaces`](src/bijux_canon_ingest/interfaces) for CLI and HTTP edges
- [`tests`](tests) for behavior, layout, and corpus-backed checks

## Read this next

- [Package guide](docs/index.md)
- [Project overview](docs/project_overview.md)
- [Layout and ownership map](docs/LAYOUT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Tests](docs/TESTS.md)
