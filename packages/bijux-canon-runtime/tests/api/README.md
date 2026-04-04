# API Test Notes

Runtime API handlers are intentionally not the main unit-testing target in this
repository.

The contract gate is the combination of:

- pinned OpenAPI artifacts
- schema stability checks
- schemathesis-style behavioral validation

The primary failure mode we care about here is contract drift, not whether a
thin handler function has perfect line coverage. Coverage percentages can be
misleading when most API behavior is delegated to runtime services behind the
boundary.
