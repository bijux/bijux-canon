# Architecture

The package should read as deterministic transforms in the middle, adapters at
the edges, and package workflows that stay easy to trace.

## Main layers

- `processing/`, `core/`, and `retrieval/` hold durable ingest and retrieval logic
- `domain/` defines protocols and effect descriptions
- `application/` assembles package workflows
- `infra/` and `integrations/` implement concrete adapters
- `interfaces/` exposes CLI and HTTP boundaries
- `observability/` records what happened during ingest work

## Intended flow

1. A boundary receives a request or source document set.
2. Application code selects the appropriate ingest workflow.
3. Deterministic transforms in `processing/` and related modules shape the content.
4. Retrieval-oriented assembly prepares package-local outputs.
5. Boundary code serializes results without absorbing core ingest logic.
