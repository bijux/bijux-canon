# Public API

This package has no end-user console contract, but it does have a repository API.

## Repository-facing API

- `bijux_canon_dev.api.*`
- `bijux_canon_dev.quality.*`
- `bijux_canon_dev.security.*`
- `bijux_canon_dev.sbom.*`
- `bijux_canon_dev.release.*`
- `bijux_canon_dev.packages.*`

If a root target, CI workflow, or cross-package test imports a module directly,
that module should be treated as public within this repository.

## Maintenance rule

Prefer small, named entrypoints over deep imports into implementation details.
That keeps the automation surface legible and easier to refactor safely.
