# Contracts

`bijux-canon-dev` does not expose an end-user application API, but it still has
real contracts inside the repository.

## Stable repository-facing contracts

- module entrypoints used by root `make` targets
- helpers called directly by CI or packaging workflows
- package-maintenance helpers that tests and automation import by name

Examples include:

- `bijux_canon_dev.quality.*`
- `bijux_canon_dev.security.*`
- `bijux_canon_dev.sbom.*`
- `bijux_canon_dev.release.*`
- `bijux_canon_dev.api.*`
- selected `bijux_canon_dev.packages.*` helpers

If changing a helper would require changing root automation or CI at the same
time, treat it as a contract change and make that change intentionally.
