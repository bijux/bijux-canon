# Freeze Criteria

`bijux-canon-index` is ready for a release freeze only when a maintainer can
answer "yes" to all of these questions without hand-waving.

## Release checklist

- do the root package targets pass: `make PACKAGE=bijux-canon-index lint`, `quality`, and `test`
- do public boundary artifacts match the intended surface
- do replay, comparison, and provenance flows still pass on supported paths
- do package docs still explain the actual contract surface and failure semantics
- is the package tree free of accidental runtime state and caches

## Artifacts that must move with public changes

- CLI help or flag snapshots
- OpenAPI output
- compatibility snapshots
- docs under `docs/spec/`

If a reviewer would need to infer the new contract from code alone, the package
is not ready to freeze yet.
