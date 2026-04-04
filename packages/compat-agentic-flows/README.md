# agentic-flows

`agentic-flows` is the continuation of the published `agentic-flows`
distribution on PyPI. Each release keeps the legacy distribution, import, and
command surfaces available while installing `bijux-canon-runtime` at the same
version.

This package exists to reduce migration breakage, not to become the preferred
entrypoint for new work.

## Publication status

- published continuation of the legacy `agentic-flows` distribution
- each release depends on `bijux-canon-runtime==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- command: `bijux-canon-runtime`

## What this compatibility package preserves

- the legacy distribution name `agentic-flows`
- the legacy Python import surface `agentic_flows`
- the legacy command name `agentic-flows`

## Read this next

Depend on `bijux-canon-runtime` directly and read the canonical docs there:

- package directory: [`../bijux-canon-runtime`](../bijux-canon-runtime)
- package docs: [`../bijux-canon-runtime/docs/index.md`](../bijux-canon-runtime/docs/index.md)
- changelog: [CHANGELOG.md](CHANGELOG.md)

## Primary entrypoint

- console script: `agentic-flows`

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- [CHANGELOG.md](CHANGELOG.md)
