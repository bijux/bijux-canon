# Layout

`bijux-canon-ingest` has a broad tree, so the layout needs to communicate
ownership clearly instead of relying on tribal knowledge.

## How to read the tree

- `application/` is where package workflows are assembled
- `config/` holds ingest-facing configuration models and builders
- `core/` holds durable ingest rules and shared value helpers
- `domain/` defines pure contracts and package semantics
- `infra/` and `integrations/` are where concrete adapters live
- `interfaces/` is for CLI, HTTP, serialization, and boundary translation
- `observability/` describes what happened during ingest work
- `processing/` holds deterministic document transforms
- `retrieval/` holds ingest-local retrieval models and assembly

## Support subpackages that need discipline

`fp/`, `result/`, `streaming/`, `tree/`, and `safeguards/` can be useful, but
they should stay narrow and package-relevant. They should not become a dumping
ground for generic utilities that no one can place elsewhere.

## What should not drift into this tree

- standalone vector execution engines
- runtime-wide storage or replay governance
- repository tooling and release helpers
- business logic that properly belongs to another canonical package

## Test layout expectations

- `tests/unit/` should mirror meaningful source ownership
- `tests/e2e/` should protect package-facing flows
- `tests/eval/` should hold pinned retrieval and corpus assets
- `tests/invariants/` should defend layout rules and generated-file hygiene
