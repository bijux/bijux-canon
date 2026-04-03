# TESTS

`bijux-canon-runtime` validates behavior through:
- `tests/unit/` for local runtime behavior
- `tests/api/` for HTTP contracts
- `tests/e2e/` for flow execution scenarios
- `tests/regression/` for replay, determinism, and storage guarantees
- `tests/smoke/` for focused store and wiring checks

Changes to replay semantics, persistence, or runtime contracts should land with targeted regression coverage.
