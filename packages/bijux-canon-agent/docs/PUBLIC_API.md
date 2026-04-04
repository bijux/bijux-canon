# Public API

The public surface of `bijux-canon-agent` should be small, deliberate, and easy
to explain.

## Supported entrypoints

- console script: `bijux-canon-agent`
- distribution and import package: `bijux_canon_agent`
- CLI boundary module: `bijux_canon_agent.interfaces.cli.entrypoint`
- HTTP boundary package: `bijux_canon_agent.api.v1`

## Not automatically public

Modules under `agents/`, `pipeline/`, `application/`, and `observability/` are
implementation space unless they are explicitly documented as stable.

## Maintenance rule

Prefer adding a clear public wrapper over telling users to import deep internal
modules directly. That keeps refactors possible without turning every file move
into a breaking change.
