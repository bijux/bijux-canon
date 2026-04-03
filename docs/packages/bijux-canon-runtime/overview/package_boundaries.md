# Package Boundaries

`bijux-canon-runtime` should stay focused on governed execution and replay. The package
becomes clumsy when it absorbs domain logic, authoring concerns, or package-specific
integrations that belong elsewhere in the canon.

## What Belongs In Runtime

- Manifest resolution and execution planning.
- Runtime authority, determinism enforcement, and replay acceptability.
- Trace capture, diffing, persisted execution records, and audit evidence.
- Schema-backed API and CLI surfaces for run, replay, inspect, diff, explain, and validate.

## What Belongs In Neighbor Packages

- `bijux-canon-agent`: agent pipeline composition and reusable workflow authoring.
- `bijux-canon-reason`: reasoning strategies, evaluation suites, and replay analysis logic
  that is not part of the canonical execution lifecycle.
- `bijux-canon-ingest`: retrieval assembly, ingestion flows, and corpus-facing adapters.
- `bijux-canon-index`: indexing, search, and identity or drift analysis for indexed assets.

## Boundary Checks

- If a module is primarily about planning or executing a run, it probably belongs here.
- If a module is primarily about a specific agent, index, corpus, or reasoning strategy,
  it probably belongs in a sibling package instead.
- If a feature needs to bypass replay or determinism rules, it should not be added to the
  stable runtime surface.
