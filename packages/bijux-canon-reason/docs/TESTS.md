# Tests

The test layout mirrors the package's biggest risks: reasoning drift,
verification drift, and boundary drift.

## Main layers

- `tests/unit/` for local models and runtime behavior
- `tests/e2e/` for package-facing flows
- `tests/docs/` for docs-facing checks
- `tests/perf/` for performance-focused checks

Within `tests/e2e/`, the subdirectories cover CLI, API, replay gates, smoke
flows, retrieval reasoning, and evaluation-oriented behavior.

Changes to reasoning flow, verification semantics, or public interfaces should
land with matching tests in the layer that would catch the regression.
