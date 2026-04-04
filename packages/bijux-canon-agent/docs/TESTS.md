# Tests

Tests in `bijux-canon-agent` are arranged to answer different kinds of risk.

## Test layers

- `tests/unit/` for local logic, models, and narrow orchestration behavior
- `tests/integration/` for cross-module collaboration inside the package
- `tests/e2e/` for realistic workflows and operator-facing expectations
- `tests/api/` for HTTP contract behavior
- `tests/invariants/` for architecture rules and repository discipline
- `tests/fixtures/`, `tests/snapshots/`, and `tests/stubs/` for deterministic support material

## What to add when changing behavior

- add unit tests when changing local decisions or models
- add integration or e2e coverage when changing workflow sequencing
- add API coverage when changing request or response semantics
- add invariant coverage when changing layout rules or public surface expectations

Good docs tell people where to look. Good tests make that guidance executable.
