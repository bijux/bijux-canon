# bijux-vex

`bijux-vex` is the continuation of the published `bijux-vex` distribution on
PyPI. Each release keeps the legacy distribution, import, and command surfaces
available while installing `bijux-canon-index` at the same version.

## Publication status

- published continuation of the legacy `bijux-vex` distribution
- each release depends on `bijux-canon-index==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-index`
- Python import: `bijux_canon_index`
- command: `bijux-canon-index`

## What this compatibility package preserves

- the legacy distribution name `bijux-vex`
- the legacy Python import surface `bijux_vex`
- the legacy command name `bijux-vex`

## What to do for new work

Use `bijux-canon-index` directly:

- package directory: [`../bijux-canon-index`](../bijux-canon-index)
- package docs: [`../bijux-canon-index/docs/index.md`](../bijux-canon-index/docs/index.md)
- changelog: [CHANGELOG.md](CHANGELOG.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- [CHANGELOG.md](CHANGELOG.md)
