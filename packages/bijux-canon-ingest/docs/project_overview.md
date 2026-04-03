# Project Overview

`bijux-canon-ingest` is the package responsible for deterministic document
ingestion and package-local retrieval assembly in the `bijux-canon` monorepo.

What this package owns:

- document cleaning, chunking, and deterministic ingest transforms
- package-local retrieval assembly and in-memory index workflows
- package-facing CLI and HTTP boundaries
- ingest-specific adapters, tracing, and observability helpers

What this package should not own:

- standalone vector execution engines or cross-package index authorities
- runtime-wide replay governance, storage authority, or workflow coordination
- monorepo tooling, release automation, or general developer infrastructure
- generic shared foundations that deserve extraction into a dedicated package

Current source shape:

- `src/bijux_canon_ingest/application/`: orchestration and service flows
- `src/bijux_canon_ingest/config/`: ingest-facing configuration models and builders
- `src/bijux_canon_ingest/core/`: durable rules, shared value helpers, and core types
- `src/bijux_canon_ingest/domain/`: pure protocols and effect descriptions
- `src/bijux_canon_ingest/infra/`: concrete adapters
- `src/bijux_canon_ingest/interfaces/`: CLI, HTTP, serialization, and edge helpers
- `src/bijux_canon_ingest/observability/`: deterministic trace and observation models
- `src/bijux_canon_ingest/processing/`: pure ingest transforms and streaming stages
- `src/bijux_canon_ingest/retrieval/`: retrieval contracts, indexes, and retrieval models

Extraction candidates:

- `fp/`, `result/`, `streaming/`, `tree/`, `safeguards/`, and parts of `integrations/`
  are still useful here, but they are generic enough that another dedicated shared
  package may eventually own them if multiple packages need the same abstractions.
- Until then, they should stay dependency-light and free of package-external business
  logic so extraction remains straightforward.

Quality priorities:

1. `src/` should reflect clear ownership boundaries and stable public surfaces.
2. `tests/` should protect behavior, structure, and repository hygiene.
3. `docs/` should explain the package in durable language that still makes sense years later.
