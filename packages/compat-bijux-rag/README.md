# bijux-rag

`bijux-rag` is the compatibility package for the old ingest distribution name.
Its job is to keep legacy installs and imports working while the canonical
package name is `bijux-canon-ingest`.

## Canonical package

- `bijux-canon-ingest`

## What this compatibility package preserves

- the legacy distribution name `bijux-rag`
- the legacy Python import surface `bijux_rag`
- the legacy command name `bijux-rag`

## What to do for new work

Use `bijux-canon-ingest` directly:

- package directory: [`../bijux-canon-ingest`](../bijux-canon-ingest)
- package docs: [`../bijux-canon-ingest/docs/index.md`](../bijux-canon-ingest/docs/index.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
