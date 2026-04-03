# TESTS

`bijux-canon-index` verifies behavior through:
- `tests/unit/` for structure and public-surface checks
- `tests/conformance/` for backend and determinism rules
- `tests/e2e/`, `tests/scenarios/`, and `tests/stress/` for workload realism
- plugin contract tests under `plugins/template_plugin/tests/`

Changes to backend behavior, API contracts, or plugin surfaces should ship with matching coverage.
