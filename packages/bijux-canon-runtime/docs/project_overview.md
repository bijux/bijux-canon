# Runtime Project Overview

`bijux-canon-runtime` owns deterministic execution, replay, runtime evidence capture,
and the contracts that make those behaviors auditable. It should be the package where
teams resolve a manifest, execute a governed run, persist a trace, and replay that run
under explicit acceptance criteria.

## Ideal Tree

```text
src/bijux_canon_runtime/
  api/v1/            HTTP entrypoint and schema-backed surface
  application/       Planning, execution orchestration, replay coordination
  contracts/         Contract validators for manifests, plans, artifacts, traces
  core/              Runtime authority, failure taxonomy, cross-cutting invariants
  interfaces/cli/    Operator CLI boundary
  model/             Runtime data models grouped by artifact, execution, flows, reasoning
  observability/     Capture, classification, diffing, and storage of execution evidence
  ontology/          Stable identifiers, enums, and public value surfaces
  runtime/           Execution engines, stores, and lifecycle internals
  verification/      Verification workflows that remain runtime-owned
```

## Package Boundaries

- `bijux-canon-runtime` should own execution semantics, replay semantics, trace storage,
  and evidence needed to audit a run.
- `bijux-canon-agent` should own agent composition and pipeline authoring, not replay
  storage or runtime persistence rules.
- `bijux-canon-reason` should own reasoning strategies and evaluation logic, not the
  canonical runtime lifecycle.
- `bijux-canon-ingest` and `bijux-canon-index` should own retrieval/indexing behavior,
  not execution authority or runtime trace governance.

## Smells To Avoid

- Example assets or exploratory notes living under `src/`.
- Generic names like `experimental`, `main`, or package-comparison docs that do not
  explain runtime responsibility.
- Cross-package logic hidden inside runtime when it really belongs to agent, reason,
  ingest, or index.
