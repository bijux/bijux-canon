# Tests

The runtime test layout mirrors the package's biggest risks: replay drift,
determinism drift, and persistence drift.

## Main layers

- `tests/unit/` for local runtime behavior
- `tests/api/` for HTTP contract protection
- `tests/e2e/` for flow execution scenarios
- `tests/regression/` for replay, determinism, and storage guarantees
- `tests/smoke/` for focused store and wiring checks

Changes to replay semantics, persistence, or runtime contracts should land with
targeted regression coverage, not just unit tests.
