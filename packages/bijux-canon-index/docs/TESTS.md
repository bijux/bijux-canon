# Tests

The test layout reflects the package's biggest risks: backend drift,
provenance drift, and replay drift.

## Main layers

- `tests/unit/` for local behavior and public model checks
- `tests/conformance/` for backend and determinism guarantees
- `tests/e2e/`, `tests/scenarios/`, and `tests/stress/` for realistic execution pressure
- plugin contract tests under `plugins/template_plugin/tests/`

## What to add when changing behavior

- add conformance coverage when changing backend or replay rules
- add schema or API coverage when boundary behavior changes
- add plugin coverage when extension points or capability reports change
