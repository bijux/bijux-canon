# Freeze Criteria

`bijux-canon-index` is ready for a release freeze only when these conditions hold:
- root package targets pass: `make PACKAGE=bijux-canon-index lint`, `quality`, and `test`
- CLI help and flag snapshots match the intended public surface
- OpenAPI output and compatibility snapshots remain stable or are updated intentionally
- replay, comparison, and provenance flows pass across the supported deterministic paths
- package docs still describe the current contract surface and failure semantics
- no runtime state files or caches leak into the package tree

Changes that alter public contracts must update the corresponding freeze artifact in the same review:
- CLI help or flags
- OpenAPI output
- compatibility snapshots
- required package docs under `docs/spec/` and `docs/maintainer/`
