# bijux-agent

`bijux-agent` is the continuation of the published `bijux-agent` distribution
on PyPI. Each release keeps the legacy distribution, import, and command
surfaces available while installing `bijux-canon-agent` at the same version.

## Publication status

- published continuation of the legacy `bijux-agent` distribution
- each release depends on `bijux-canon-agent==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-agent`
- Python import: `bijux_canon_agent`
- command: `bijux-canon-agent`

## What this compatibility package preserves

- the legacy distribution name `bijux-agent`
- the legacy Python import surface `bijux_agent`
- the legacy command name `bijux-agent`

## Read this next

Use `bijux-canon-agent` directly:

- package directory: [`../bijux-canon-agent`](../bijux-canon-agent)
- package docs: [`../bijux-canon-agent/docs/index.md`](../bijux-canon-agent/docs/index.md)
- changelog: [CHANGELOG.md](CHANGELOG.md)

## Primary entrypoint

- console script: `bijux-agent`

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- [CHANGELOG.md](CHANGELOG.md)
