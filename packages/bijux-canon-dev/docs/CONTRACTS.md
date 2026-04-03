# CONTRACTS

Stable contracts in `bijux-canon-dev` are module entrypoints used by repository automation:
- `bijux_canon_dev.quality.deptry_scan`
- `bijux_canon_dev.security.pip_audit_gate`
- `bijux_canon_dev.sbom.requirements_writer`
- `bijux_canon_dev.release.version_resolver`
- `bijux_canon_dev.api.openapi_drift`
- selected `bijux_canon_dev.packages.*` helpers

These contracts are internal to the monorepo but should still change intentionally because `make`, CI, and tests depend on them.
