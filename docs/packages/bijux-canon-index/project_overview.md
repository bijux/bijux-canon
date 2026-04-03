# bijux-canon-index package overview

`bijux-canon-index` owns contract-driven vector execution. It materializes execution artifacts, runs deterministic and non-deterministic requests, compares outcomes, and records provenance for replay and audit. It should not absorb retrieval orchestration, general RAG flows, application-specific serving logic, or unrelated plugin examples.

## Intended tree

```text
src/bijux_canon_index/
  api/v1/                HTTP boundary
  application/
    orchestration/       execution bootstrap, dispatch, and result bookkeeping
                         engine wiring and package-facing facades
  contracts/             resource and backend-facing contracts
  core/                  stable execution types, identities, runtime primitives
  domain/
    algorithms/          algorithm declarations
    artifact/            artifact creation and lifecycle
    drift/               backend drift detection
    non_determinism/     ANN planning and randomness rules
    provenance/          replay and lineage
    requests/            request planning, execution, comparison, scoring
  infra/                 adapters, ledgers, env/config integration
  interfaces/            CLI, schemas, serialization, error mapping
  tooling/               benchmarks and package-maintenance helpers
```

## Ownership rules

- `application/` wires flows together but does not own policy.
- `application/orchestration/` is where execution bootstrap, request normalization, and run/artifact bookkeeping live.
- `domain/` owns execution semantics, request rules, and provenance logic.
- `infra/` adapts storage, ANN backends, vector stores, logging, and runtime configuration.
- `interfaces/` translates external payloads and command/API boundaries into core requests.
- `tooling/` may support package maintenance, but it should not become runtime behavior.

## Current posture

The package is now much closer to the intended shape:

- source root matches the distribution name
- boundary code is separated from orchestration
- orchestration internals are split into runtime bootstrap, execution runtime, and result bookkeeping helpers
- vague buckets like `monitoring` and `nd` were replaced with durable names
- request internals read as planning, execution, comparison, and result collection instead of overloaded generic modules
- identity drift from `bijux-canon-index` is being retired from package-facing surfaces

The remaining standard to protect is discipline, not another rename wave: keep vector execution here, and push cross-package workflow concerns back to the packages that own them.
