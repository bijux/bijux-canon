# TESTS

`bijux-canon-ingest` coverage is organized around:
- `tests/unit/` for local module behavior
- `tests/e2e/` for package-facing flows
- `tests/eval/` for pinned corpus and retrieval assets

Changes to transforms, retrieval behavior, or public boundaries should land with focused tests in the matching layer.
