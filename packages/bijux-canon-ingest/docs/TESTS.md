# Tests

The test layout matches the package's main risks: transform drift, retrieval
drift, and layout drift.

## Main layers

- `tests/unit/` for local module behavior
- `tests/e2e/` for package-facing flows
- `tests/eval/` for pinned corpus and retrieval assets
- `tests/invariants/` for layout and repository hygiene rules

## What to add when behavior changes

- add unit coverage when changing transforms or models
- add e2e coverage when changing CLI, HTTP, or workflow behavior
- add eval coverage when changing retrieval-facing output against fixed corpora
