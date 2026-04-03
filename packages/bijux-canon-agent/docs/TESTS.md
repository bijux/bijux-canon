# TESTS

`bijux-canon-agent` test coverage is organized around:
- `tests/unit/` for local behavior and public models
- `tests/invariants/` for architecture and repository discipline
- `tests/api/` for HTTP contract behavior
- `tests/e2e/` and `tests/integration/` for workflow realism

Changes to public behavior, traces, or boundaries should land with focused tests in the matching layer.
