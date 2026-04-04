# bijux-rag

`bijux-rag` is the continuation of the published `bijux-rag` distribution on
PyPI. Each release keeps the legacy distribution, import, and command surfaces
available while installing `bijux-canon-ingest` at the same version.

## Publication status

- published continuation of the legacy `bijux-rag` distribution
- each release depends on `bijux-canon-ingest==<same version>`
- intended for existing environments that still rely on the legacy name

## Canonical package

- distribution: `bijux-canon-ingest`
- Python import: `bijux_canon_ingest`
- command: `bijux-canon-ingest`

## What this compatibility package preserves

- the legacy distribution name `bijux-rag`
- the legacy Python import surface `bijux_rag`
- the legacy command name `bijux-rag`

## What to do for new work

Use `bijux-canon-ingest` directly:

- package directory: [`../bijux-canon-ingest`](../bijux-canon-ingest)
- package docs: [`../bijux-canon-ingest/docs/index.md`](../bijux-canon-ingest/docs/index.md)
- changelog: [CHANGELOG.md](CHANGELOG.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- [CHANGELOG.md](CHANGELOG.md)
