# Undefined behavior (maintainer)

Undefined behavior is where bugs hide. This page lists areas that are intentionally not promised.

## Examples

- model output quality or completeness
- provider stability and tokenization drift
- performance and throughput
- cross-run caching semantics (unless explicitly specified)

## Rule

If a behavior matters to integrators, it must move from “undefined” to “specified”:
write it in `docs/spec/*`, add tests where feasible, and version it.
